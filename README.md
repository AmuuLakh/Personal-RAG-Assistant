# 🎓 Personal RAG Assistant

<p align="center">
  <strong>An AI-powered study companion that turns your course materials into intelligent, citation-backed study workspaces.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Status-Complete-brightgreen?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/React-Vite-61DAFB?style=for-the-badge&logo=react&logoColor=black" />
  <img src="https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/ChromaDB-Vector%20Store-orange?style=for-the-badge" />
</p>

---

## 📖 Overview

**Personal RAG Assistant** is an AI-powered study tool built using **Retrieval-Augmented Generation (RAG)**. It transforms personal course materials—including lecture slides, syllabi, and multi-page textbook PDFs—into isolated, memory-enabled study workspaces.

Unlike generic AI chatbots, the assistant prioritizes your actual course materials, providing context-aware answers with precise page-level citations.

### ✨ Why I Built This

Generic AI chatbots can hallucinate, mix information across unrelated subjects, or provide external definitions that contradict what a professor teaches.

I built Personal RAG Assistant to address three key problems:

| Problem | Solution |
|---|---|
| ❌ AI hallucinations | 📚 Strict grounding in uploaded course PDFs with source citations |
| ❌ Mixed conversation context | 🔒 Isolated document storage for every chat session |
| ❌ Forgetful conversations | 🧠 Persistent chat history and context-aware follow-up memory |

---

## 🚀 Key Features

### 📚 1. Strict Grounding & Source Citations
- Generates answers strictly from uploaded course materials.
- Provides interactive `[Source X]` citation cards.
- Displays the exact filename, page number, and quoted source snippet.
- Makes it easy to verify every answer against the original material.

### 🔒 2. Multi-Session Document Isolation
- Create separate workspaces for different classes, subjects, or projects.
- Each chat maintains its own isolated vector knowledge base.
- ChromaDB metadata filtering ensures documents never bleed across sessions.

### 🧠 3. Conversational Follow-Up Memory
- Remembers previous messages within each chat session.
- Injects the last 6 conversation messages into the LLM prompt.
- Enhances semantic search using recent conversational context.
- Supports natural follow-ups such as:
  - "What are the next steps for that project?"
  - "Can you explain that formula more simply?"
  - "What was the second method we discussed?"

### ⚡ 4. Optimized PDF Ingestion
- Page-by-page PDF extraction using `pypdf`.
- Overlapping text chunking (800 characters).
- Batch embeddings (25 chunks per request).
- Automatic exponential backoff for API rate limits.
- ChromaDB ID deduplication for reliable indexing.

### 🔄 5. Resilient AI Model Fallback
- Automatically switches between configured Gemini models.
- Handles temporary API errors and high-demand (503) responses.
- Improves reliability when a model becomes temporarily unavailable.

### 💾 6. Persistent Local Storage
- SQLite-powered chat history.
- Automatically generated chat titles based on uploaded PDFs.
- Persistent conversation turns and citation metadata.
- Local PDF storage and vector indexing.

---

## 🏗️ System Architecture

The application uses a React frontend, FastAPI backend, ChromaDB vector database, and SQLite conversation storage.

```text
┌─────────────────────────────┐
│       React + Vite          │
│       Tailwind CSS          │
│                             │
│  • Multi-Chat Sidebar       │
│  • Drag & Drop PDF Upload   │
│  • Citation Inspector       │
└──────────────┬──────────────┘
               │
       1. Upload PDF / Ask
          Question (chat_id)
               │
               ▼
┌─────────────────────────────┐
│       FastAPI Backend       │
│                             │
│  • PDF Ingestion Pipeline   │
│  • RAG Orchestration        │
│  • Context + History        │
│  • Gemini Model Fallback    │
└───────┬──────────────┬──────┘
        │              │
  2. Embeddings    3. Read/Write
  & Vector Search      History
        │              │
        ▼              ▼
┌───────────────┐  ┌────────────────┐
│   ChromaDB    │  │     SQLite     │
│               │  │                │
│ • Embeddings  │  │ • Chat Sessions│
│ • PDF Chunks  │  │ • Messages     │
│ • Metadata    │  │ • Citations    │
│ • chat_id     │  │ • Timestamps   │
└───────────────┘  └────────────────┘
```

### 🔍 Retrieval & Isolation

Every document chunk is tagged with metadata:

```python
{
    "chat_id": active_chat_id,
    "source": filename,
    "page": page_number
}
```

When a user asks a question, ChromaDB applies a session-specific metadata filter:

```python
where={"chat_id": active_chat_id}
```

This ensures that retrieval only searches documents belonging to the active conversation.

---

## 🛠️ Tech Stack

| Layer | Technologies |
|---|---|
| Frontend | React, Vite, Tailwind CSS |
| Backend | Python, FastAPI |
| LLM | Google Gemini API |
| Embeddings | Gemini embedding model |
| Vector Database | ChromaDB |
| Relational Database | SQLite |
| PDF Processing | pypdf |
| Development | Git, npm, Python virtual environments |

---

## 💡 Engineering Highlights

Some of the most important engineering decisions behind this project:

| Component | Implementation |
|---|---|
| **Session Isolation** | Every vector chunk is tagged with a `chat_id` and retrieved using metadata filtering. |
| **Persistent Memory** | SQLite stores chat sessions, messages, titles, and serialized citation cards across restarts. |
| **Context-Aware Retrieval** | The last 6 messages are incorporated into the prompt and recent context is used to improve search queries. |
| **Batch Embeddings** | Embeddings are processed in batches of 25 to reduce API overhead and support larger PDFs. |
| **Rate-Limit Handling** | Exponential backoff handles `429 RESOURCE_EXHAUSTED` errors. |
| **Vector Deduplication** | ChromaDB IDs prevent duplicate document chunks during indexing. |
| **Model Resilience** | Configured Gemini models provide an automatic fallback chain for temporary service failures. |
| **Local Privacy** | Uploaded PDFs, vector indexes, chat history, and API keys remain on the local machine. |

---

## 📁 Project Structure

```text
Personal-RAG-Assistant/
│
├── backend/
│   ├── main.py              # FastAPI endpoints and orchestration
│   ├── rag_engine.py        # PDF processing, embeddings, RAG pipeline
│   ├── database.py          # SQLite schema and CRUD operations
│   ├── requirements.txt     # Python dependencies
│   └── .env                 # Local Gemini API key (git-ignored)
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Main multi-chat application UI
│   │   └── index.css        # Tailwind CSS entry point
│   │
│   ├── package.json         # Node dependencies
│   └── vite.config.js       # Vite configuration
│
├── .gitignore               # Excludes sensitive and generated files
└── README.md
```

---

## ⚙️ Installation & Setup

Follow these steps to run the application locally.

### Prerequisites

Make sure you have the following installed:

- **Python 3.10+** — [Download Python](https://www.python.org/downloads/)
- **Node.js 18+** — [Download Node.js](https://nodejs.org/)
- **Git** — [Download Git](https://git-scm.com/)
- **Google Gemini API Key** — [Get a free API key](https://aistudio.google.com/apikey)

### 1. Clone the Repository

Open your terminal and run:

```bash
git clone https://github.com/AmuuLakh/Personal-RAG-Assistant.git

cd Personal-RAG-Assistant
```

### 2. Set Up the Backend

Navigate to the backend directory:

```bash
cd backend
```

Create a Python virtual environment:

```bash
python -m venv venv
```

Activate it:

**Windows (PowerShell):**

```powershell
.\venv\Scripts\activate
```

**macOS / Linux:**

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### 3. Configure Your Gemini API Key

Create a `.env` file inside the `backend/` directory.

**Windows (PowerShell):**

```powershell
Set-Content -Path .env -Value "GEMINI_API_KEY=your_actual_gemini_api_key_here"
```

**macOS / Linux:**

```bash
echo "GEMINI_API_KEY=your_actual_gemini_api_key_here" > .env
```

Replace `your_actual_gemini_api_key_here` with your API key from Google AI Studio.

> ⚠️ Never commit your `.env` file or expose your API key publicly.

### 4. Start the Backend Server

From inside the `backend/` directory:

```bash
python -m uvicorn main:app --reload
```

If everything is configured correctly, you should see:

```text
INFO: Application startup complete.
Uvicorn running on http://127.0.0.1:8000
```

Backend API documentation:

[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Keep this terminal running.

### 5. Set Up the Frontend

Open a **second terminal** and navigate to the frontend directory from the project root:

```bash
cd Personal-RAG-Assistant/frontend
```

Install the dependencies:

```bash
npm install
```

Start the Vite development server:

```bash
npm run dev
```

You should see:

```text
Local: http://localhost:5173/
```

### 6. Launch the Application

Open your browser and visit:

**http://localhost:5173**

Your Personal RAG Assistant is now running locally! 🎉

---

## 🔐 Privacy & Data Storage

This application is designed around local-first data storage.

- Uploaded PDFs are stored locally.
- ChromaDB vector indexes remain on your machine.
- SQLite stores conversation history locally.
- API credentials are stored in a local `.env` file.
- Sensitive files and generated databases are excluded from Git.

**Note:** Document content sent to external Gemini API services for embedding or generation is subject to Google's API data-handling policies. Local storage does not mean all processing stays offline.

---

## 📄 License

This project is available under the **MIT License**.

---

<p align="center">
  <strong>Built with ❤️ to make studying smarter, more organized, and more reliable.</strong>
  <br/>
  <sub>Personal RAG Assistant — Your course materials. Your knowledge base. Your AI study companion.</sub>
</p>