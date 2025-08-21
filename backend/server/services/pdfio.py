from typing import Tuple, Dict, Any
from pypdf import PdfReader

def extract_text_and_meta(path: str) -> Tuple[str, Dict[str, Any]]:
    reader = PdfReader(path)
    text_parts = []
    for page in reader.pages:
        try:
            text_parts.append(page.extract_text() or "")
        except Exception:
            # ignore broken pages
            pass
    text = "\n".join(text_parts).strip()

    meta = {}
    try:
        info = reader.metadata or {}
        if info.get("/Title"):
            meta["title"] = info.get("/Title")
        if info.get("/Author"):
            meta["authors"] = info.get("/Author")
    except Exception:
        pass

    meta["source_path"] = path
    return text, meta