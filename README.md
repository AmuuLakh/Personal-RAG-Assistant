# 🎓 Personal RAG Assistant

> **Status:** ✅ Complete & Running Locally (Multi-Session Chat Memory + Per-Chat Vector Isolation)

An AI-powered study companion built with **Retrieval-Augmented Generation (RAG)** that turns personal course materials—lecture slides, syllabi, and multi-page textbook PDFs—into isolated, memory-enabled study workspaces with exact page citations.

---

## 💡 Why I Built This
Generic AI chatbots frequently hallucinate, mix up context across unrelated subjects, or give outside definitions that contradict what a professor actually teaches in class. I built **Personal RAG Assistant** to solve three real student pain points:
1. **Strict Grounding & Receipts:** Every answer is synthesized strictly from uploaded course PDFs and includes interactive `[Source X]` citation cards showing the exact filename, page number, and quoted snippet.
2. **Per-Chat Document Isolation:** Each study session has its own isolated knowledge base—so your *Machine Learning* PDFs never bleed into your *Database Systems* chat.
3. **Conversational Follow-Up Memory:** Remembers prior turns within a chat session so you can ask natural follow-ups (e.g., *"What are the next steps for that project?"* or *"Explain that formula simply"*) without repeating context.

---

## 🏗️ System Architecture

```text
┌─────────────────────────┐   1. Upload PDF (chat_id)    ┌──────────────────────────────────────────┐
│                         │ ───────────────────────────► │  FastAPI Ingestion Pipeline              │
│   React + Vite          │                              │  • Page-by-page extraction (pypdf)       │
│   Tailwind CSS UI       │                              │  • Overlapping chunking (800 chars)      │
│                         │ ◄─────────────────────────── │  • Rate-limited batch embeddings (25/req)│
│  • Multi-Chat Sidebar   │   5. Cited Answer +          └────────────────────┬─────────────────────┘
│  • Drag & Drop Upload   │      Source Cards                                 │ 2. Upsert Tagged Vectors
│  • Citation Inspector   │                                                   ▼
└───────────┬─────────────┘                              ┌──────────────────────────────────────────┐
            │                                            │  ChromaDB (Local Vector Store)           │
            │ 3. Ask Question (chat_id)                  │  • Stores embeddings + metadata:         │
            ▼                                            │    {chat_id, source, page}               │
┌─────────────────────────┐   4a. Metadata Filter        │  • Filtered search: where={chat_id}      │
│   FastAPI Orchestrator  │ ───────────────────────────► └──────────────────────────────────────────┘
│   (main.py)             │
│                         │   4b. Read/Write History     ┌──────────────────────────────────────────┐
│  • Context + History    │ ───────────────────────────► │  SQLite (chat_history.db)                │
│    Prompt Builder       │                              │  • chats table (id, title, created_at)   │
│  • Auto Model Fallback  │                              │  • messages table (role, content, cites) │
└─────────────────────────┘                              └──────────────────────────────────────────┘




📁 Project Structure

Personal-RAG-Assistant/
├── backend/
│   ├── main.py              # FastAPI REST endpoints (/chats, /upload, /chat) + CORS
│   ├── rag_engine.py        # PDF chunking, batch embeddings, ChromaDB search, Gemini RAG
│   ├── database.py          # SQLite schema & CRUD helpers for persistent chat history
│   ├── requirements.txt     # Python dependencies
│   └── .env                 # Local API key (git-ignored — created during setup)
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Multi-chat UI, drag-and-drop uploader, citation cards
│   │   └── index.css        # Tailwind CSS v4 entry
│   ├── package.json         # Node dependencies
│   └── vite.config.js       # Vite + Tailwind plugin config
├── .gitignore               # Protects .env, uploads/, chroma_db/, and chat_history.db
└── README.md




🚀 Complete Local Setup Guide (Step-by-Step)
Follow these steps to clone and run the full stack locally in under 3 minutes.

Prerequisites
Python 3.10+ installed (Download Python)

Node.js 18+ (LTS) installed (Download Node.js)

Git installed

A free Google Gemini API Key from Google AI Studio

Step 1: Clone the Repository
Open a terminal (PowerShell on Windows, or Terminal on macOS/Linux) and run:

Bash
git clone [https://github.com/AmuuLakh/Personal-RAG-Assistant.git](https://github.com/AmuuLakh/Personal-RAG-Assistant.git)
cd Personal-RAG-Assistant
Step 2: Set Up & Start the Backend (Terminal 1)
Navigate into the backend folder and create a virtual environment:

Bash
cd backend
python -m venv venv
Activate the virtual environment:

Windows (PowerShell):

PowerShell
.\venv\Scripts\activate
macOS / Linux:

Bash
source venv/bin/activate
(You should now see (venv) at the start of your terminal prompt.)

Install the Python dependencies:

Bash
pip install -r requirements.txt
Create a .env file inside backend/ containing your Gemini API key:

Windows (PowerShell):

PowerShell
Set-Content -Path .env -Value "GEMINI_API_KEY=your_actual_gemini_api_key_here"
macOS / Linux:

Bash
echo "GEMINI_API_KEY=your_actual_gemini_api_key_here" > .env
(Replace your_actual_gemini_api_key_here with your real key from Google AI Studio.)

Start the FastAPI server:

Bash
python -m uvicorn main:app --reload
Verification: You should see INFO: Application startup complete. and Uvicorn running on http://127.0.0.1:8000. Interactive API docs are available at http://127.0.0.1:8000/docs. Leave this terminal running.

Step 3: Set Up & Start the Frontend (Terminal 2)
Open a second terminal window and navigate to the frontend folder from the project root:

Bash
cd Personal-RAG-Assistant/frontend
Install the Node packages:

Bash
npm install
Start the Vite development server:

Bash
npm run dev
Verification: You should see Local: http://localhost:5173/.

Step 4: Using the App
Open http://localhost:5173 in your browser.