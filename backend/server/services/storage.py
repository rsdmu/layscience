import os
import uuid
import shutil
from typing import Tuple

from fastapi import UploadFile

BASE_UPLOADS = os.getenv("UPLOADS_DIR", "uploads")

def _ensure_dir(path: str):
    try:
        os.makedirs(path, exist_ok=True)
        return path
    except Exception:
        # fall back to tmp
        fallback = os.path.join(os.getenv("TMPDIR", "/tmp"), "uploads")
        os.makedirs(fallback, exist_ok=True)
        return fallback

def save_upload(file: UploadFile) -> Tuple[str, str]:
    folder = _ensure_dir(BASE_UPLOADS)
    ext = (file.filename.rsplit(".", 1)[-1] if "." in file.filename else "pdf").lower()
    name = f"{uuid.uuid4()}.{ext}"
    path = os.path.join(folder, name)
    with open(path, "wb") as out:
        shutil.copyfileobj(file.file, out)
    return name, os.path.abspath(path)
