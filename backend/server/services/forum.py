"""Simple SQLite-backed forum storage.

Provides helper functions to persist feedback topics and replies.
Defaults to storing data under ``data/forum.sqlite3`` but honours
``FORUM_DB_PATH`` environment variable so deployments can point to a
PostgreSQL database via appropriate connection string.
"""

import os
import sqlite3
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional

# Determine DB path and ensure directory exists
DB_PATH = os.getenv("FORUM_DB_PATH") or os.path.join(
    os.getenv("DATA_DIR", "data"), "forum.sqlite3"
)

try:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
except Exception:
    # fallback to /tmp if provided path not writable
    DB_PATH = os.path.join("/tmp", "forum.sqlite3")
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

_conn_lock = threading.Lock()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, isolation_level=None)
    conn.row_factory = sqlite3.Row
    with conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute(
            """CREATE TABLE IF NOT EXISTS topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            email TEXT,
            created_at TEXT NOT NULL
        )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS replies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
            body TEXT NOT NULL,
            email TEXT,
            created_at TEXT NOT NULL
        )"""
        )
    return conn


_conn = _connect()


# ---------------------------------------------------------------------------
# Topic helpers
# ---------------------------------------------------------------------------


def create_topic(title: str, body: str, email: Optional[str] = None) -> int:
    """Create a new feedback topic and return its ID."""
    now = datetime.utcnow().isoformat()
    with _conn_lock, _conn:
        cur = _conn.execute(
            "INSERT INTO topics (title, body, email, created_at) VALUES (?, ?, ?, ?)",
            (title, body, email, now),
        )
        return cur.lastrowid


def list_topics(page: int = 1, page_size: int = 20) -> List[Dict[str, Any]]:
    """Return paginated list of topics, newest first."""
    offset = (page - 1) * page_size
    cur = _conn.execute(
        "SELECT id, title, body, email, created_at FROM topics ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (page_size, offset),
    )
    return [dict(row) for row in cur.fetchall()]


# ---------------------------------------------------------------------------
# Reply helpers
# ---------------------------------------------------------------------------


def create_reply(topic_id: int, body: str, email: Optional[str] = None) -> int:
    """Create a reply for a given topic."""
    now = datetime.utcnow().isoformat()
    with _conn_lock, _conn:
        cur = _conn.execute(
            "INSERT INTO replies (topic_id, body, email, created_at) VALUES (?, ?, ?, ?)",
            (topic_id, body, email, now),
        )
        return cur.lastrowid


def list_replies(topic_id: int) -> List[Dict[str, Any]]:
    """List replies for a topic ordered by creation time."""
    cur = _conn.execute(
        "SELECT id, topic_id, body, email, created_at FROM replies WHERE topic_id = ? ORDER BY created_at ASC",
        (topic_id,),
    )
    return [dict(row) for row in cur.fetchall()]
