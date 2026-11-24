import os
import time
from pypdf import PdfReader
import chromadb
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# 1. Initialize Gemini Client (reads GEMINI_API_KEY from .env automatically)
client = genai.Client()

# 2. Initialize Local Persistent ChromaDB (saves to ./chroma_db folder)
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(name="student_notes")


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> list[str]:
    """Splits text into overlapping chunks so context isn't lost at boundaries."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def get_embedding(text: str) -> list[float]:
    """Converts a single string of text into a vector (used for user questions)."""
    result = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text,
    )
    return result.embeddings[0].values


def get_embeddings_batch(texts: list[str], max_retries: int = 5) -> list[list[float]]:
    """Embeds a batch of chunks with automatic retry if the free-tier TPM limit is hit."""
    for attempt in range(max_retries):
        try:
            result = client.models.embed_content(
                model="gemini-embedding-001",
                contents=texts,
            )
            return [emb.values for emb in result.embeddings]
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                wait_seconds = 15 * (attempt + 1)
                print(f"[Rate Limit] 30k TPM cap reached. Waiting {wait_seconds}s before retrying...")
                time.sleep(wait_seconds)
            else:
                raise e
    raise RuntimeError("Exceeded max retries due to Gemini free-tier rate limits.")


def ingest_pdf(file_path: str, filename: str, batch_size: int = 25) -> int:
    """Reads a PDF, skips already-indexed chunks, and embeds within the 30k tokens/min free limit."""
    reader = PdfReader(file_path)

    all_ids = []
    all_docs = []
    all_metas = []

    for page_num, page in enumerate(reader.pages, start=1):
        raw_text = page.extract_text() or ""
        if not raw_text.strip():
            continue

        chunks = chunk_text(raw_text)
        for idx, chunk in enumerate(chunks):
            all_ids.append(f"{filename}_p{page_num}_c{idx}")
            all_docs.append(chunk)
            all_metas.append({"source": filename, "page": page_num})

    if not all_docs:
        raise ValueError("No readable text found in this PDF (it might be a scanned image PDF).")

    # Check which chunk IDs are already stored so we never waste tokens re-embedding them
    existing = set(collection.get(ids=all_ids)["ids"])
    new_ids, new_docs, new_metas = [], [], []
    for cid, doc, meta in zip(all_ids, all_docs, all_metas):
        if cid not in existing:
            new_ids.append(cid)
            new_docs.append(doc)
            new_metas.append(meta)

    if not new_docs:
        return len(all_docs)

    # Process in 25-chunk batches (~5,000 tokens each) with pacing to stay under 30k tokens/min
    for i in range(0, len(new_docs), batch_size):
        batch_ids = new_ids[i : i + batch_size]
        batch_docs = new_docs[i : i + batch_size]
        batch_metas = new_metas[i : i + batch_size]

        batch_embeddings = get_embeddings_batch(batch_docs)

        collection.upsert(
            ids=batch_ids,
            embeddings=batch_embeddings,
            documents=batch_docs,
            metadatas=batch_metas,
        )

        # Pace at ~12 seconds per 5k-token batch (~25k tokens/min) so we stay safely under 30k TPM
        if i + batch_size < len(new_docs):
            time.sleep(12.0)

    return len(all_docs)


def ask_question(question: str, top_k: int = 4) -> dict:
    """Finds the top_k most relevant chunks and generates a cited answer with model fallback."""
    if collection.count() == 0:
        return {
            "answer": "Your knowledge base is empty! Upload a syllabus, lecture slide deck, or PDF note first.",
            "citations": [],
        }

    # 1. Embed the student's question
    query_embedding = get_embedding(question)

    # 2. Retrieve top_k closest chunks from ChromaDB
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
    )

    retrieved_docs = results["documents"][0]
    retrieved_metas = results["metadatas"][0]

    # 3. Format context with explicit source tags for the LLM
    context_blocks = []
    citations = []

    for i, (doc, meta) in enumerate(zip(retrieved_docs, retrieved_metas), start=1):
        source_label = f"{meta['source']} (Page {meta['page']})"
        context_blocks.append(f"[Source {i}: {source_label}]\n{doc}")
        citations.append(
            {
                "id": i,
                "source": meta["source"],
                "page": meta["page"],
                "snippet": doc[:220] + "..." if len(doc) > 220 else doc,
            }
        )

    formatted_context = "\n\n---\n\n".join(context_blocks)

    # 4. Grounded Generation Prompt with automatic fallback across Gemini models
    system_instruction = (
        "You are an AI Study Assistant for a university student. "
        "Answer the student's question using ONLY the provided course material excerpts. "
        "Cite your sources inline using [Source X] notation. "
        "If the provided excerpts do not contain enough information to answer the question, "
        "explicitly say: 'I couldn't find that in your uploaded notes.' Do NOT guess or use outside facts."
    )

    prompt = f"COURSE MATERIAL EXCERPTS:\n{formatted_context}\n\nSTUDENT QUESTION:\n{question}"

    fallback_models = ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-4-hydrogen"]
    last_error = None

    for model_name in fallback_models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.2,
                ),
            )
            return {
                "answer": response.text,
                "citations": citations,
            }
        except Exception as e:
            last_error = e
            if "503" in str(e) or "UNAVAILABLE" in str(e) or "429" in str(e):
                print(f"[Model Fallback] {model_name} busy, switching to next model...")
                time.sleep(1.5)
                continue
            raise e

    raise RuntimeError(f"All Gemini models are temporarily busy. Last error: {last_error}")


def list_uploaded_sources() -> list[str]:
    """Returns unique filenames currently stored in ChromaDB."""
    if collection.count() == 0:
        return []
    data = collection.get(include=["metadatas"])
    sources = sorted({meta["source"] for meta in data["metadatas"]})
    return sources