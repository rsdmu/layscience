"""
Enhanced jobs module for LayScience with robust database path handling.

This module mirrors the original jobs.py functionality but adds logic to
determine a writable location for the SQLite database. In environments
where the default working directory is read‑only (such as many
serverless platforms), attempting to connect to a file like
``jobs.sqlite3`` can result in a ``sqlite3.OperationalError`` with
``attempt to write a readonly database``. To mitigate this, we check
whether the directory containing the database is writable. If not, we
fall back to a location under the system temporary directory (``/tmp``)
which is usually writable. Additionally, you can override the database
location via the ``JOBS_DB_PATH`` environment variable.
"""

import os
import json
import sqlite3
import threading
import tempfile
from typing import Optional, Dict, Any

_CONN_LOCK = threading.Lock()

# Determine a safe database path.  The environment variable
# ``JOBS_DB_PATH`` always takes precedence.  If it's not provided, we
# default to ``jobs.sqlite3`` in the current directory.  If that
# directory is not writable, we fall back to a file in the system
# temporary directory.  This logic prevents ``attempt to write a
# readonly database`` errors when running in read‑only environments.
def _determine_db_path() -> str:
    # Honour explicit configuration first.
    env_path = os.getenv("JOBS_DB_PATH")
    if env_path:
        return env_path
    # Start with a relative file in the current working directory.
    candidate = "jobs.sqlite3"
    directory = os.path.dirname(os.path.abspath(candidate)) or os.getcwd()
    try:
        # Check write permission on the directory.  We use os.access
        # because merely opening a connection may succeed in read‑only
        # mode but writes will fail later.
        if os.access(directory, os.W_OK):
            return candidate
    except Exception:
        # In case of unexpected failures, fall through to tmp.
        pass
    # Fallback: use a file in the system temporary directory.
    tmp_dir = tempfile.gettempdir()
    return os.path.join(tmp_dir, "layscience_jobs.sqlite3")


# Global database path for this module.
_DB_PATH = _determine_db_path()


def _get_conn() -> sqlite3.Connection:
    """Create or return a SQLite connection with schema initialization.

    This helper attempts to connect to the configured database path and
    automatically falls back to the system temporary directory if the
    initial connection fails due to an inability to open or write the
    database file.  Without this guard, environments with read‑only
    file systems would throw a cryptic ``OperationalError`` when
    creating or committing to the database.  The fallback path is
    deterministic (``/tmp/layscience_jobs.sqlite3``) so multiple
    instances can share state if desired.
    """
    path = _DB_PATH
    try:
        conn = sqlite3.connect(path, check_same_thread=False)
    except sqlite3.OperationalError:
        # If the explicit path is not writable, fallback to /tmp
        tmp_path = os.path.join(tempfile.gettempdir(), "layscience_jobs.sqlite3")
        conn = sqlite3.connect(tmp_path, check_same_thread=False)
    # Ensure the jobs table exists
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs(
            id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            request_json TEXT,
            payload_json TEXT,
            error TEXT
        )
        """
    )
    return conn


_CONN = _get_conn()


def create(req: Dict[str, Any]) -> str:
    """Create a new job record and return its ID.

    The ID is prefixed with ``sum_`` for clarity.  We wrap the insert
    operation in a lock to ensure thread safety.  Any exceptions are
    propagated to the caller (e.g. FastAPI) where they will be logged
    and turned into HTTP 500 errors.
    """
    import secrets
    job_id = "sum_" + secrets.token_hex(6)
    with _CONN_LOCK:
        _CONN.execute(
            "INSERT OR REPLACE INTO jobs(id, status, request_json) VALUES(?,?,?)",
            (job_id, "running", json.dumps(req)),
        )
        _CONN.commit()
    return job_id


def get(job_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a job record by ID.

    Returns ``None`` if no job exists with the given ID.  Deserializes
    the JSON fields into native Python objects.
    """
    with _CONN_LOCK:
        cur = _CONN.execute(
            "SELECT id, status, request_json, payload_json, error FROM jobs WHERE id=?",
            (job_id,),
        )
        row = cur.fetchone()
    if not row:
        return None
    return {
        "id": row[0],
        "status": row[1],
        "request": json.loads(row[2]) if row[2] else None,
        "payload": json.loads(row[3]) if row[3] else None,
        "error": row[4],
    }


def finish(job_id: str, payload: Dict[str, Any]) -> None:
    """Mark a job as done and store its payload."""
    with _CONN_LOCK:
        _CONN.execute(
            "UPDATE jobs SET status=?, payload_json=?, error=NULL WHERE id=?",
            ("done", json.dumps(payload), job_id),
        )
        _CONN.commit()


def fail(job_id: str, error: str) -> None:
    """Mark a job as failed and record an error message."""
    with _CONN_LOCK:
        _CONN.execute(
            "UPDATE jobs SET status=?, error=? WHERE id=?",
            ("failed", error, job_id),
        )
        _CONN.commit()