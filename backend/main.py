import os
import uuid
import shutil
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from rag_engine import ingest_pdf, ask_question, list_uploaded_sources, delete_chat_vectors
from database import (
    init_db,
    create_chat,
    update_chat_title,
    list_chats,
    delete_chat,
    save_message,
    get_messages,
)

init_db()

app = FastAPI(title="Personal RAG Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


class ChatRequest(BaseModel):
    chat_id: str
    question: str


@app.get("/chats")
def get_all_chats():
    chats = list_chats()
    if not chats:
        default_id = f"chat_{uuid.uuid4().hex[:8]}"
        create_chat(default_id, "Study Session 1")
        chats = list_chats()
    return {"chats": chats}


@app.post("/chats")
def new_chat():
    chat_id = f"chat_{uuid.uuid4().hex[:8]}"
    count = len(list_chats()) + 1
    title = f"Study Session {count}"
    create_chat(chat_id, title)
    return {"id": chat_id, "title": title}


@app.delete("/chats/{chat_id}")
def remove_chat(chat_id: str):
    delete_chat(chat_id)
    delete_chat_vectors(chat_id)
    return {"status": "deleted"}


@app.get("/chats/{chat_id}")
def get_chat_details(chat_id: str):
    return {
        "messages": get_messages(chat_id),
        "documents": list_uploaded_sources(chat_id),
    }


@app.post("/upload")
async def upload_document(chat_id: str = Form(...), file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported right now.")

    chat_upload_dir = os.path.join(UPLOAD_DIR, chat_id)
    os.makedirs(chat_upload_dir, exist_ok=True)
    file_path = os.path.join(chat_upload_dir, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        chunks_created = ingest_pdf(file_path, file.filename, chat_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")

    # Auto-name the chat after the first uploaded PDF if it still has a generic title
    existing_docs = list_uploaded_sources(chat_id)
    if len(existing_docs) == 1:
        clean_title = file.filename.rsplit(".", 1)[0][:32]
        update_chat_title(chat_id, clean_title)

    return {
        "filename": file.filename,
        "chunks_indexed": chunks_created,
        "message": f"Indexed {chunks_created} chunks from {file.filename}",
    }


@app.post("/chat")
def chat_with_notes(request: ChatRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    history = get_messages(request.chat_id)
    save_message(request.chat_id, "user", request.question)

    try:
        result = ask_question(request.question, request.chat_id, history)
        save_message(request.chat_id, "assistant", result["answer"], result["citations"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")