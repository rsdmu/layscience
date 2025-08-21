
import os
from typing import Optional

LOCAL_UPLOAD_DIR = os.getenv("LOCAL_UPLOAD_DIR", "uploads")

def local_path_for(file_id: str) -> str:
    return os.path.join(LOCAL_UPLOAD_DIR, f"{file_id}.pdf")
