from typing import Tuple, Dict, Any

from pypdf import PdfReader

from . import errors as err

def extract_text_and_meta(path: str) -> Tuple[str, Dict[str, Any]]:
    try:
        reader = PdfReader(path)
    except Exception as e:  # pragma: no cover - rare
        raise err.UserFacingError(
            code="invalid_pdf",
            public_message="Could not read the uploaded PDF.",
            where="extract_text_and_meta",
            hint="Ensure the file is a valid PDF.",
        ) from e

    text_parts = []
    for page in reader.pages:
        try:
            text_parts.append(page.extract_text() or "")
        except Exception:
            # ignore broken pages
            pass
    text = "\n".join(text_parts).strip()

    meta: Dict[str, Any] = {}
    try:
        info = reader.metadata or {}
        if info.get("/Title"):
            meta["title"] = info.get("/Title")
        if info.get("/Author"):
            meta["authors"] = info.get("/Author")
    except Exception:  # pragma: no cover - metadata issues
        pass

    meta["source_path"] = path
    return text, meta
