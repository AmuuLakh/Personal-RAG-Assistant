import { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import {
  BookOpen,
  UploadCloud,
  FileText,
  Send,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Loader2,
  GraduationCap,
} from "lucide-react";

const API_BASE = "http://127.0.0.1:8000";

const STARTER_PROMPTS = [
  "Summarize the main topics covered in my uploaded notes.",
  "What are the key definitions or formulas I should memorize for the exam?",
  "Create 5 practice quiz questions based strictly on these documents.",
];

function CitationCard({ citation }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border border-slate-700/70 bg-slate-900/60 rounded-lg overflow-hidden text-xs">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-3 py-2 text-left hover:bg-slate-800/70 transition-colors"
      >
        <div className="flex items-center gap-2 text-indigo-300 font-medium truncate">
          <span className="px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
            Source {citation.id}
          </span>
          <span className="truncate">{citation.source}</span>
          <span className="text-slate-400 shrink-0">• Page {citation.page}</span>
        </div>
        {expanded ? (
          <ChevronUp className="w-3.5 h-3.5 text-slate-400 shrink-0" />
        ) : (
          <ChevronDown className="w-3.5 h-3.5 text-slate-400 shrink-0" />
        )}
      </button>

      {expanded && (
        <div className="px-3 py-2.5 border-t border-slate-800 bg-slate-950/70 text-slate-300 leading-relaxed font-mono text-[11px]">
          "{citation.snippet}"
        </div>
      )}
    </div>
  );
}

export default function App() {
  const [documents, setDocuments] = useState([]);
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Welcome to your **Personal RAG Assistant**. Upload a syllabus, lecture slide deck, or study PDF on the left—then ask me anything about your course material.",
      citations: [],
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [isDragging, setIsDragging] = useState(false);

  const fileInputRef = useRef(null);
  const chatEndRef = useRef(null);

  useEffect(() => {
    fetchDocuments();
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  async function fetchDocuments() {
    try {
      const res = await fetch(`${API_BASE}/documents`);
      const data = await res.json();
      setDocuments(data.documents || []);
    } catch (err) {
      console.error("Failed to fetch documents:", err);
    }
  }

  async function handleFileUpload(file) {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setUploadStatus({ type: "error", text: "Please upload a PDF file." });
      return;
    }

    setIsUploading(true);
    setUploadStatus(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API_BASE}/upload`, {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Upload failed");

      setUploadStatus({
        type: "success",
        text: `Indexed ${data.chunks_indexed} chunks from ${data.filename}`,
      });
      await fetchDocuments();
    } catch (err) {
      setUploadStatus({ type: "error", text: err.message });
    } finally {
      setIsUploading(false);
    }
  }

  async function handleSendMessage(questionText = input) {
    const trimmed = questionText.trim();
    if (!trimmed || isLoading) return;

    const userMsg = { role: "user", content: trimmed };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: trimmed }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to get answer");

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.answer,
          citations: data.citations || [],
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `**Error:** ${err.message}. Make sure your FastAPI backend is running on port 8000.`,
          citations: [],
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 font-sans antialiased">
      {/* LEFT SIDEBAR: Knowledge Base & Upload */}
      <aside className="w-80 border-r border-slate-800/80 bg-slate-900/40 flex flex-col justify-between p-5 shrink-0">
        <div className="space-y-6">
          {/* Brand Header */}
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-indigo-600/20 border border-indigo-500/30 text-indigo-400">
              <GraduationCap className="w-6 h-6" />
            </div>
            <div>
              <h1 className="font-semibold text-base tracking-tight text-white">
                Personal RAG Assistant
              </h1>
              <p className="text-xs text-slate-400">Grounded Study Companion</p>
            </div>
          </div>

          {/* Drag & Drop Upload Box */}
          <div>
            <label className="block text-xs font-medium uppercase tracking-wider text-slate-400 mb-2">
              Upload Course Material
            </label>
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setIsDragging(false);
                const file = e.dataTransfer.files[0];
                handleFileUpload(file);
              }}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-5 text-center cursor-pointer transition-all ${
                isDragging
                  ? "border-indigo-400 bg-indigo-500/10"
                  : "border-slate-700/80 hover:border-indigo-500/60 hover:bg-slate-800/40"
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                className="hidden"
                onChange={(e) => handleFileUpload(e.target.files[0])}
              />
              {isUploading ? (
                <div className="flex flex-col items-center gap-2 py-2">
                  <Loader2 className="w-6 h-6 text-indigo-400 animate-spin" />
                  <p className="text-xs text-slate-300">Chunking & embedding PDF...</p>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-2">
                  <UploadCloud className="w-7 h-7 text-indigo-400" />
                  <p className="text-xs font-medium text-slate-200">
                    Drop PDF here or <span className="text-indigo-400 underline">browse</span>
                  </p>
                  <p className="text-[11px] text-slate-500">
                    Syllabi, lecture slides, or study notes
                  </p>
                </div>
              )}
            </div>

            {uploadStatus && (
              <div
                className={`mt-3 flex items-start gap-2 p-2.5 rounded-lg text-xs border ${
                  uploadStatus.type === "success"
                    ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
                    : "bg-rose-500/10 border-rose-500/30 text-rose-300"
                }`}
              >
                {uploadStatus.type === "success" ? (
                  <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
                ) : (
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                )}
                <span>{uploadStatus.text}</span>
              </div>
            )}
          </div>

          {/* Indexed Documents List */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
                Indexed Notes ({documents.length})
              </span>
              <BookOpen className="w-3.5 h-3.5 text-slate-500" />
            </div>

            {documents.length === 0 ? (
              <p className="text-xs text-slate-500 italic py-3 px-3 rounded-lg bg-slate-900/60 border border-slate-800/60">
                No PDFs indexed yet. Upload a document above to start asking questions.
              </p>
            ) : (
              <ul className="space-y-1.5 max-h-60 overflow-y-auto pr-1">
                {documents.map((doc) => (
                  <li
                    key={doc}
                    className="flex items-center gap-2.5 px-3 py-2 rounded-lg bg-slate-800/50 border border-slate-700/50 text-xs text-slate-200"
                  >
                    <FileText className="w-4 h-4 text-indigo-400 shrink-0" />
                    <span className="truncate" title={doc}>
                      {doc}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        {/* Footer Badge */}
        <div className="pt-4 border-t border-slate-800/80 text-[11px] text-slate-500 flex items-center justify-between">
          <span>FastAPI + ChromaDB</span>
          <span className="text-indigo-400 font-medium">Gemini RAG</span>
        </div>
      </aside>

      {/* MAIN CHAT PANEL */}
      <main className="flex-1 flex flex-col min-w-0">
        {/* Top Bar */}
        <header className="h-14 border-b border-slate-800/80 px-6 flex items-center justify-between bg-slate-950/80 backdrop-blur">
          <div className="flex items-center gap-2 text-sm text-slate-300">
            <Sparkles className="w-4 h-4 text-indigo-400" />
            <span>Answers strictly grounded in your uploaded documents</span>
          </div>
          <span className="text-xs px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            ● Citations Enabled
          </span>
        </header>

        {/* Messages Feed */}
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
          <div className="max-w-3xl mx-auto space-y-6">
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[85%] rounded-2xl px-5 py-3.5 text-sm leading-relaxed ${
                    msg.role === "user"
                      ? "bg-indigo-600 text-white shadow-lg shadow-indigo-950/40"
                      : "bg-slate-900 border border-slate-800 text-slate-200"
                  }`}
                >
                  <div className="prose prose-invert prose-sm max-w-none">
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </div>

                  {/* Source Citations */}
                  {msg.citations && msg.citations.length > 0 && (
                    <div className="mt-4 pt-3 border-t border-slate-800/90 space-y-2">
                      <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                        Retrieved Sources (Click to inspect)
                      </p>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {msg.citations.map((cit) => (
                          <CitationCard key={cit.id} citation={cit} />
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-slate-900 border border-slate-800 rounded-2xl px-5 py-3.5 flex items-center gap-2.5 text-sm text-slate-400">
                  <Loader2 className="w-4 h-4 text-indigo-400 animate-spin" />
                  <span>Searching your notes and verifying citations...</span>
                </div>
              </div>
            )}

            <div ref={chatEndRef} />
          </div>
        </div>

        {/* Starter Chips + Input Box */}
        <div className="border-t border-slate-800/80 bg-slate-950 px-6 py-4">
          <div className="max-w-3xl mx-auto space-y-3">
            {messages.length === 1 && (
              <div className="flex flex-wrap gap-2">
                {STARTER_PROMPTS.map((prompt) => (
                  <button
                    key={prompt}
                    onClick={() => handleSendMessage(prompt)}
                    className="text-xs px-3 py-1.5 rounded-full bg-slate-900 hover:bg-slate-800 border border-slate-700/80 text-slate-300 transition-colors text-left"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            )}

            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendMessage();
              }}
              className="flex items-center gap-3 bg-slate-900 border border-slate-700/80 focus-within:border-indigo-500 rounded-xl px-4 py-2.5 transition-colors"
            >
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask a question about your uploaded notes..."
                className="flex-1 bg-transparent text-sm text-white placeholder-slate-500 focus:outline-none"
              />
              <button
                type="submit"
                disabled={isLoading || !input.trim()}
                className="p-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:hover:bg-indigo-600 text-white transition-colors"
              >
                <Send className="w-4 h-4" />
              </button>
            </form>
          </div>
        </div>
      </main>
    </div>
  );
}