# 🎓 Personal RAG Assistant

> **Status:** 🚧 Active Development (Full-Stack RAG App Live — Implementing Multi-Chat Isolation & Conversation Memory Next)

An AI-powered study companion that connects large language models to your personal course materials—lecture slides, syllabi, and textbook PDFs—using **Retrieval-Augmented Generation (RAG)** to deliver accurate, grounded answers with exact page citations.

---

## 💡 Why I Built This
Generic AI chatbots frequently hallucinate or pull outside definitions that contradict what a professor actually teaches in class. As a student, I wanted an assistant that:
1. **Answers strictly from my own notes** (and explicitly says *"I couldn't find that in your uploaded notes"* when information isn't there).
2. **Shows its receipts** by citing the exact PDF filename, page number, and quoted text snippet behind every answer.
3. **Handles large multi-page textbooks reliably** on free-tier cloud APIs using token-aware batching, deduplication, and automatic model fallback.

---

## 🏗️ How It Works (Architecture)

```text
┌───────────────────┐     1. Upload PDF      ┌────────────────────────────────────────┐
│                   │ ─────────────────────► │  FastAPI Ingestion Pipeline            │
│   React + Vite    │                        │  • Page-by-page text extraction        │
│   Tailwind UI     │                        │  • Overlapping chunking (800 chars)    │
│                   │ ◄───────────────────── │  • Rate-limited batch embeddings       │
└───────────────────┘   4. Cited Answer +    └───────────────────┬────────────────────┘
         │                 Source Snippets                       │ 2. Store Vectors
         │                                                       ▼
         │              3. Semantic Search   ┌────────────────────────────────────────┐
         └─────────────────────────────────► │  ChromaDB (Local Vector Store)       │
                        (Top-K Cosine Match) │  Stores embeddings + page metadata     │
                                             └────────────────────────────────────────┘