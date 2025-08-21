import hashlib, os, time

def new_id(prefix="sum") -> str:
    return f"{prefix}_{hashlib.sha1(os.urandom(16)).hexdigest()[:12]}"

def is_probably_scanned(pdf_bytes: bytes) -> bool:
    return pdf_bytes.count(b"BT") < 2

def compute_readability(text: str):
    try:
        import textstat
        fk = textstat.flesch_kincaid_grade(text)
        ease = textstat.flesch_reading_ease(text)
        return {"flesch_kincaid_grade": float(fk), "flesch_reading_ease": float(ease)}
    except Exception:
        return {"flesch_kincaid_grade": -1.0, "flesch_reading_ease": -1.0}

def detect_disclaimers(text: str):
    t = text.lower()
    out = []
    if any(w in t for w in ["randomized", "trial", "treatment", "patients", "diagnosis", "therapy", "risk factor"]):
        out.append("Health: Not medical advice.")
    if any(w in t for w in ["stock", "portfolio", "investment", "trading", "returns"]):
        out.append("Finance: Not investment advice.")
    if any(w in t for w in ["regulatory", "law", "statute", "liability"]):
        out.append("Legal: Not legal advice.")
    return out
