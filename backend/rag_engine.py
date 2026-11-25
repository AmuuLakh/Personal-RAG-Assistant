import os
import time
from pypdf import PdfReader
import chromadb
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

client = genai.Client()
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(name="student_notes")


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> list[str]:
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
    result = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text,
    )
    return result.embeddings[0].values


def get_embeddings_batch(texts: list[str], max_retries: int = 5) -> list[list[float]]:
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


def ingest_pdf(file_path: str, filename: str, chat_id: str, batch_size: int = 25) -> int:
    """Indexes a PDF tagged specifically to one chat_id so chats never mix documents."""
    reader = PdfReader(file_path)

    all_ids, all_docs, all_metas = [], [], []

    for page_num, page in enumerate(reader.pages, start=1):
        raw_text = page.extract_text() or ""
        if not raw_text.strip():
            continue

        chunks = chunk_text(raw_text)
        for idx, chunk in enumerate(chunks):
            all_ids.append(f"{chat_id}_{filename}_p{page_num}_c{idx}")
            all_docs.append(chunk)
            all_metas.append({"chat_id": chat_id, "source": filename, "page": page_num})

    if not all_docs:
        raise ValueError("No readable text found in this PDF (it might be a scanned image PDF).")

    existing = set(collection.get(ids=all_ids)["ids"])
    new_ids, new_docs, new_metas = [], [], []
    for cid, doc, meta in zip(all_ids, all_docs, all_metas):
        if cid not in existing:
            new_ids.append(cid)
            new_docs.append(doc)
            new_metas.append(meta)

    if not new_docs:
        return len(all_docs)

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

        if i + batch_size < len(new_docs):
            time.sleep(12.0)

    return len(all_docs)


def ask_question(question: str, chat_id: str, history: list[dict], top_k: int = 5) -> dict:
    """Searches ONLY documents in chat_id and uses recent conversation history for follow-ups."""
    chat_chunks = collection.get(where={"chat_id": chat_id}, include=[])
    total_for_chat = len(chat_chunks["ids"])

    if total_for_chat == 0:
        return {
            "answer": "This chat has no documents yet! Upload 1 or more PDFs in the sidebar for this chat first.",
            "citations": [],
        }

    # Combine last user turn with current question so follow-ups ("what about its deadline?") retrieve accurately
    recent_user_turns = [m["content"] for m in history if m["role"] == "user"][-2:]
    search_query = " ".join(recent_user_turns + [question]) if recent_user_turns else question
    query_embedding = get_embedding(search_query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, total_for_chat),
        where={"chat_id": chat_id},
    )

    retrieved_docs = results["documents"][0]
    retrieved_metas = results["metadatas"][0]

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

    # Format last 6 messages as conversation memory
    recent_history = history[-6:]
    history_text = "\n".join(
        f"{'Student' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
        for m in recent_history
    )

    system_instruction = (
        "You are an AI Study Assistant for a university student. "
        "Answer the student's question using ONLY the provided course material excerpts from this chat. "
        "Use the Recent Conversation History to understand pronouns and follow-up questions (e.g. 'it', 'that project', 'explain more'). "
        "Cite your sources inline using [Source X] notation. "
        "If the provided excerpts do not contain enough information, say: "
        "'I couldn't find that in the documents uploaded to this chat.' Do NOT guess or use outside facts."
    )

    prompt = (
        f"RECENT CONVERSATION HISTORY:\n{history_text or 'None'}\n\n"
        f"COURSE MATERIAL EXCERPTS:\n{formatted_context}\n\n"
        f"CURRENT STUDENT QUESTION:\n{question}"
    )

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
                print(f"[Model Fallback] {model_name} busy, switching...")
                time.sleep(1.5)
                continue
            raise e

    raise RuntimeError(f"All Gemini models are temporarily busy. Last error: {last_error}")


def list_uploaded_sources(chat_id: str) -> list[str]:
    """Returns unique filenames uploaded to a specific chat."""
    data = collection.get(where={"chat_id": chat_id}, include=["metadatas"])
    if not data["metadatas"]:
        return []
    return sorted({meta["source"] for meta in data["metadatas"]})


def delete_chat_vectors(chat_id: str):
    """Deletes all vector chunks belonging to a deleted chat."""
    collection.delete(where={"chat_id": chat_id})