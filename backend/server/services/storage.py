"""Helper functions for saving uploaded PDF files to disk."""

import os
import uuid
import shutil
from typing import Tuple

from fastapi import UploadFile


BASE_UPLOADS = os.getenv("UPLOADS_DIR", "uploads")


def _ensure_dir(path: str) -> str:
    """Create directory if it does not exist.  Fall back to /tmp/uploads on failure."""
    try:
        os.makedirs(path, exist_ok=True)
        return path
    except Exception:
        fallback = os.path.join(os.getenv("TMPDIR", "/tmp"), "uploads")
        os.makedirs(fallback, exist_ok=True)
        return fallback


def save_upload(file: UploadFile) -> Tuple[str, str]:
    """
    Save an uploaded file to the configured uploads directory.  Returns the
    randomised filename and absolute path.  Uses the file’s original extension
    if present, defaulting to ``.pdf``.
    """
    folder = _ensure_dir(BASE_UPLOADS)
    ext = (file.filename.rsplit(".", 1)[-1] if "." in file.filename else "pdf").lower()
    name = f"{uuid.uuid4()}.{ext}"
    path = os.path.join(folder, name)
    with open(path, "wb") as out:
        shutil.copyfileobj(file.file, out)
    return name, os.path.abspath(path)
