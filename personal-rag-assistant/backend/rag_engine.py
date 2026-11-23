import os
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
    """Converts a string of text into a numerical vector using Gemini."""
    result = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text,
    )
    return result.embeddings[0].values


def ingest_pdf(file_path: str, filename: str) -> int:
    """Reads a PDF page by page, chunks it, embeds it, and stores it in ChromaDB."""
    reader = PdfReader(file_path)
    total_chunks = 0

    for page_num, page in enumerate(reader.pages, start=1):
        raw_text = page.extract_text() or ""
        if not raw_text.strip():
            continue

        chunks = chunk_text(raw_text)

        for idx, chunk in enumerate(chunks):
            chunk_id = f"{filename}_p{page_num}_c{idx}"
            embedding = get_embedding(chunk)

            collection.upsert(
                ids=[chunk_id],
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[{"source": filename, "page": page_num}],
            )
            total_chunks += 1

    return total_chunks


def ask_question(question: str, top_k: int = 4) -> dict:
    """Finds the top_k most relevant chunks and generates a cited answer."""
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

    # 4. Grounded Generation Prompt
    system_instruction = (
        "You are an AI Study Assistant for a university student. "
        "Answer the student's question using ONLY the provided course material excerpts. "
        "Cite your sources inline using [Source X] notation. "
        "If the provided excerpts do not contain enough information to answer the question, "
        "explicitly say: 'I couldn't find that in your uploaded notes.' Do NOT guess or use outside facts."
    )

    prompt = f"COURSE MATERIAL EXCERPTS:\n{formatted_context}\n\nSTUDENT QUESTION:\n{question}"

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.2,  # Low temperature keeps answers factual and grounded
        ),
    )

    return {
        "answer": response.text,
        "citations": citations,
    }


def list_uploaded_sources() -> list[str]:
    """Returns unique filenames currently stored in ChromaDB."""
    if collection.count() == 0:
        return []
    data = collection.get(include=["metadatas"])
    sources = sorted({meta["source"] for meta in data["metadatas"]})
    return sources