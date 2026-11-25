import sqlite3
import json
from datetime import datetime

DB_PATH = "./chat_history.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            citations TEXT DEFAULT '[]',
            created_at TEXT NOT NULL,
            FOREIGN KEY (chat_id) REFERENCES chats (id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()


def create_chat(chat_id: str, title: str = "New Study Chat"):
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO chats (id, title, created_at) VALUES (?, ?, ?)",
        (chat_id, title, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def update_chat_title(chat_id: str, title: str):
    conn = get_conn()
    conn.execute("UPDATE chats SET title = ? WHERE id = ?", (title, chat_id))
    conn.commit()
    conn.close()


def list_chats() -> list[dict]:
    conn = get_conn()
    rows = conn.execute("SELECT id, title, created_at FROM chats ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_chat(chat_id: str):
    conn = get_conn()
    conn.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
    conn.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
    conn.commit()
    conn.close()


def save_message(chat_id: str, role: str, content: str, citations: list = None):
    conn = get_conn()
    conn.execute(
        "INSERT INTO messages (chat_id, role, content, citations, created_at) VALUES (?, ?, ?, ?, ?)",
        (chat_id, role, content, json.dumps(citations or []), datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def get_messages(chat_id: str) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT role, content, citations FROM messages WHERE chat_id = ? ORDER BY id ASC",
        (chat_id,),
    ).fetchall()
    conn.close()
    return [
        {
            "role": r["role"],
            "content": r["content"],
            "citations": json.loads(r["citations"]),
        }
        for r in rows
    ]