
import os
import sqlite3
import json
import threading
from datetime import datetime
from typing import Optional, Dict, Any

DB_PATH = os.getenv("JOBS_DB_PATH", "/app/data/jobs.sqlite3")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# If DB_PATH not writable (e.g., serverless), fall back to /tmp
try:
    with open(DB_PATH + ".touch", "w") as _f:
        _f.write("ok")
    os.remove(DB_PATH + ".touch")
except Exception:
    DB_PATH = "/tmp/jobs.sqlite3"

_conn_lock = threading.Lock()

def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, isolation_level=None)
    conn.row_factory = sqlite3.Row
    with conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute(
            '''CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                payload TEXT,
                result TEXT,
                error_code TEXT,
                error_message TEXT,
                error_where TEXT,
                error_hint TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )'''
        )
    return conn

_conn = _connect()

def create(job_id: str, status: str, payload: Dict[str, Any]):
    now = datetime.utcnow().isoformat()
    with _conn_lock, _conn:
        _conn.execute(
            "INSERT INTO jobs (id, status, payload, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (job_id, status, json.dumps(payload), now, now),
        )

def update(job_id: str, **fields):
    if not fields:
        return
    allowed = {"status", "result", "error_code", "error_message", "error_where", "error_hint"}
    sets = []
    params = []
    for k, v in fields.items():
        if k not in allowed:
            continue
        sets.append(f"{k} = ?")
        if k == "result":
            params.append(json.dumps(v))
        else:
            params.append(v or None)
    sets.append("updated_at = ?")
    params.append(datetime.utcnow().isoformat())
    params.append(job_id)
    with _conn_lock, _conn:
        _conn.execute(f"UPDATE jobs SET {', '.join(sets)} WHERE id = ?", params)

def get(job_id: str) -> Optional[Dict[str, Any]]:
    cur = _conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    row = cur.fetchone()
    if not row:
        return None
    out = dict(row)
    # Parse JSON fields
    for field in ("payload", "result"):
        if out.get(field):
            try:
                out[field] = json.loads(out[field])
            except Exception:
                pass
    return out

def health() -> Dict[str, Any]:
    ok = True
    try:
        with _conn_lock, _conn:
            _conn.execute("SELECT 1")
    except Exception as e:
        ok = False
        return {"ok": False, "db_path": DB_PATH, "error": repr(e)}
    return {"ok": ok, "db_path": DB_PATH}
