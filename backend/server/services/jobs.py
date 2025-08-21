import os
import json
import sqlite3
import threading
from typing import Optional, Dict, Any, Tuple

_DEFAULT_DIRS = [os.getenv("DATA_DIR", "data"), os.getenv("TMPDIR", "/tmp"), "."]

def _ensure_db_path() -> str:
    # Allow overriding via env var
    env_path = os.getenv("JOBS_DB_PATH")
    if env_path:
        dirn = os.path.dirname(env_path) or "."
        os.makedirs(dirn, exist_ok=True)
        return env_path
    # find first writable location
    for base in _DEFAULT_DIRS:
        try:
            os.makedirs(base, exist_ok=True)
            test_path = os.path.join(base, ".writetest")
            with open(test_path, "w") as f:
                f.write("ok")
            os.remove(test_path)
            return os.path.join(base, "jobs.sqlite3")
        except Exception:
            continue
    # last resort: current directory
    return "jobs.sqlite3"

_DB_PATH = _ensure_db_path()

_lock = threading.Lock()

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False, isolation_level=None)  # autocommit
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def _init():
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                payload TEXT,
                result TEXT,
                error TEXT,
                created_at DATETIME DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                updated_at DATETIME DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
            );
        """)

_init()

def healthcheck() -> Tuple[bool, str]:
    try:
        with _get_conn() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS _health (ts TEXT);")
            conn.execute("INSERT INTO _health (ts) VALUES (strftime('%Y-%m-%dT%H:%M:%fZ','now'));")
            conn.execute("DELETE FROM _health;")
        return True, f"ok (path={_DB_PATH})"
    except Exception as e:
        return False, f"db_error: {e} (path={_DB_PATH})"

def create(job_id: str, status: str, payload: Dict[str, Any]):
    with _lock, _get_conn() as conn:
        conn.execute(
            "INSERT INTO jobs(id, status, payload, result, error) VALUES (?,?,?,?,?)",
            (job_id, status, json.dumps(payload), None, None),
        )

def update(job_id: str, status: Optional[str] = None, result: Optional[Dict[str, Any]] = None, error: Optional[Dict[str, Any]] = None):
    sets = []
    params = []
    if status is not None:
        sets.append("status=?")
        params.append(status)
    if result is not None:
        sets.append("result=?")
        params.append(json.dumps(result))
    if error is not None:
        sets.append("error=?")
        params.append(json.dumps(error))
    sets.append("updated_at=(strftime('%Y-%m-%dT%H:%M:%fZ','now'))")
    sql = "UPDATE jobs SET " + ", ".join(sets) + " WHERE id=?"
    params.append(job_id)
    with _lock, _get_conn() as conn:
        conn.execute(sql, tuple(params))

def get(job_id: str) -> Optional[Dict[str, Any]]:
    with _get_conn() as conn:
        cur = conn.execute("SELECT id, status, payload, result, error, created_at, updated_at FROM jobs WHERE id=?", (job_id,))
        row = cur.fetchone()
        if not row:
            return None
        id, status, payload, result, error, created_at, updated_at = row
        return {
            "id": id,
            "status": status,
            "payload": json.loads(payload) if payload else None,
            "result": json.loads(result) if result else None,
            "error": json.loads(error) if error else None,
            "created_at": created_at,
            "updated_at": updated_at,
        }