"""Database-backed storage for user accounts and pending verification codes.

This module uses SQLAlchemy Core to talk to a PostgreSQL database specified by
the ``DATABASE_URL`` environment variable.  It falls back to no-ops when the
URL is not provided so that the rest of the application can run in a
file-based mode (used by the test-suite and local development).
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, Any

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    text,
)
from sqlalchemy.engine import make_url


DATABASE_URL = os.getenv("DATABASE_URL")


# Engine and table definitions are created lazily so that importing this module
# does not require a configured database.
engine = None
metadata = MetaData()

accounts_table = Table(
    "accounts",
    metadata,
    Column("email", String, primary_key=True),
    Column("username", String, nullable=False),
    Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
)

pending_table = Table(
    "pending_codes",
    metadata,
    Column("email", String, primary_key=True),
    Column("code", String, nullable=False),
    Column("code_hash", String, nullable=False),
    Column("username", String, nullable=False),
    Column("expires_at", DateTime, nullable=False),
    Column("attempts", Integer, nullable=False, default=0),
    Column("resent", Integer, nullable=False, default=0),
)


def init() -> None:
    """Initialise the database connection and ensure tables exist."""
    global engine
    if not DATABASE_URL or engine is not None:
        return
    # SQLAlchemy defaults to the legacy ``psycopg2`` driver when given a plain
    # ``postgresql://`` URL.  The project depends on the modern ``psycopg``
    # package instead, so ensure the driver name is adjusted automatically when
    # no explicit driver is provided.
    url = make_url(DATABASE_URL)
    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+psycopg")
    engine = create_engine(url, future=True)
    with engine.begin() as conn:
        metadata.create_all(conn)


def load_accounts() -> Dict[str, Dict[str, Any]]:
    """Return all accounts as a mapping keyed by email."""
    if not engine:
        return {}
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT email, username FROM accounts")).fetchall()
    return {row.email: {"username": row.username} for row in rows}


def load_pending_codes() -> Dict[str, Dict[str, Any]]:
    """Return all pending verification codes."""
    if not engine:
        return {}
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT email, code, code_hash, username, expires_at, attempts, resent
                FROM pending_codes
                """
            )
        ).fetchall()
    out: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        out[r.email] = {
            "code": r.code,
            "code_hash": r.code_hash,
            "username": r.username,
            "expires_at": r.expires_at,
            "attempts": r.attempts,
            "resent": r.resent,
        }
    return out


def upsert_pending_code(email: str, rec: Dict[str, Any]) -> None:
    """Insert or update a pending code record."""
    if not engine:
        return
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO pending_codes (email, code, code_hash, username, expires_at, attempts, resent)
                VALUES (:email, :code, :code_hash, :username, :expires_at, :attempts, :resent)
                ON CONFLICT (email) DO UPDATE SET
                    code = EXCLUDED.code,
                    code_hash = EXCLUDED.code_hash,
                    username = EXCLUDED.username,
                    expires_at = EXCLUDED.expires_at,
                    attempts = EXCLUDED.attempts,
                    resent = EXCLUDED.resent
                """
            ),
            {
                "email": email,
                "code": rec["code"],
                "code_hash": rec["code_hash"],
                "username": rec.get("username", ""),
                "expires_at": rec.get("expires_at"),
                "attempts": rec.get("attempts", 0),
                "resent": rec.get("resent", 0),
            },
        )


def delete_pending_code(email: str) -> None:
    if not engine:
        return
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM pending_codes WHERE email = :email"), {"email": email})


def create_account(email: str, rec: Dict[str, Any]) -> None:
    if not engine:
        return
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO accounts (email, username, created_at)
                VALUES (:email, :username, :created_at)
                ON CONFLICT (email) DO UPDATE SET username = EXCLUDED.username
                """
            ),
            {
                "email": email,
                "username": rec.get("username", ""),
                "created_at": datetime.utcnow(),
            },
        )


def delete_account(email: str) -> None:
    if not engine:
        return
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM accounts WHERE email = :email"), {"email": email})

