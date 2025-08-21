
import os
import json
import sqlite3
import threading
from typing import Optional, Dict, Any

_DB_PATH = os.getenv("JOBS_DB_PATH", "jobs.sqlite3")

# Create table if not exists
_CONN_LOCK = threading.Lock()
def _get_conn():
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS jobs(
        id TEXT PRIMARY KEY,
        status TEXT NOT NULL,
        request_json TEXT,
        payload_json TEXT,
        error TEXT
    )""")
    return conn

_CONN = _get_conn()

def create(req: Dict[str, Any]) -> str:
    import secrets
    job_id = "sum_" + secrets.token_hex(6)
    with _CONN_LOCK:
        _CONN.execute("INSERT OR REPLACE INTO jobs(id, status, request_json) VALUES(?,?,?)",
                      (job_id, "running", json.dumps(req)))
        _CONN.commit()
    return job_id

def get(job_id: str) -> Optional[Dict[str, Any]]:
    with _CONN_LOCK:
        cur = _CONN.execute("SELECT id,status,request_json,payload_json,error FROM jobs WHERE id=?",(job_id,))
        row = cur.fetchone()
    if not row:
        return None
    return {
        "id": row[0],
        "status": row[1],
        "request": json.loads(row[2]) if row[2] else None,
        "payload": json.loads(row[3]) if row[3] else None,
        "error": row[4]
    }

def finish(job_id: str, payload: Dict[str, Any]) -> None:
    with _CONN_LOCK:
        _CONN.execute("UPDATE jobs SET status=?, payload_json=?, error=NULL WHERE id=?",
                      ("done", json.dumps(payload), job_id))
        _CONN.commit()

def fail(job_id: str, error: str) -> None:
    with _CONN_LOCK:
        _CONN.execute("UPDATE jobs SET status=?, error=? WHERE id=?",
                      ("failed", error, job_id))
        _CONN.commit()
