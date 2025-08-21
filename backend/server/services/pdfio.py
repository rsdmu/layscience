
import os
import io
import re
import time
import logging
from typing import Optional
import requests
from pypdf import PdfReader

logger = logging.getLogger("layscience.pdfio")

USER_AGENT = "LayScience/2.0 (+https://example.com)"

def resolve_doi_to_pdf_url(doi: str) -> str:
    # DOI pattern check
    doi = doi.strip()
    if doi.lower().startswith("http"):
        # treat as URL
        return doi
    # resolve DOI using doi.org
    url = f"https://doi.org/{doi}"
    logger.info("Resolving DOI: %s", doi)
    r = requests.get(url, headers={"Accept":"application/pdf", "User-Agent": USER_AGENT}, allow_redirects=True, timeout=30)
    if r.status_code >= 400:
        raise RuntimeError(f"DOI resolution failed with status {r.status_code}")
    # If direct pdf content, write to bytes; else if 'location' header includes pdf.
    content_type = r.headers.get("Content-Type","")
    if "application/pdf" in content_type.lower() and r.content:
        # We actually downloaded the PDF; write to temp file
        path = _save_bytes(r.content)
        return path
    # Otherwise, try to fetch location or look for pdf link
    final_url = r.url
    # Many publishers serve pdf at url ending with .pdf
    if final_url.lower().endswith(".pdf"):
        return final_url
    # Fallback: try common patterns
    if "nature.com" in final_url and "/pdf" not in final_url and not final_url.endswith(".pdf"):
        guess = final_url.rstrip("/") + ".pdf"
        return guess
    return final_url

def fetch_pdf_from_url(url: str) -> str:
    if url.lower().startswith("http"):
        logger.info("Fetching PDF from %s", url)
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, allow_redirects=True, timeout=60)
        if r.status_code >= 400:
            raise RuntimeError(f"Failed to download PDF: HTTP {r.status_code}")
        # If content type not pdf but url ends with .pdf, still accept
        if "application/pdf" not in r.headers.get("Content-Type","").lower() and not url.lower().endswith(".pdf"):
            # Try to find a pdf link in the page
            m = re.search(r'href="([^"]+\.pdf)"', r.text, flags=re.I)
            if m:
                pdf_url = requests.compat.urljoin(url, m.group(1))
                return fetch_pdf_from_url(pdf_url)
            raise RuntimeError("URL does not point to a PDF and no PDF link found in the page")
        return _save_bytes(r.content)
    else:
        # treat as local path
        if not os.path.exists(url):
            raise FileNotFoundError(url)
        return url

def _save_bytes(content: bytes) -> str:
    import uuid, os
    os.makedirs("tmp", exist_ok=True)
    path = os.path.join("tmp", f"{uuid.uuid4().hex}.pdf")
    with open(path, "wb") as f:
        f.write(content)
    return path

def extract_text(path: str) -> str:
    logger.info("Extracting text from %s", path)
    with open(path, "rb") as f:
        reader = PdfReader(f)
        texts = []
        for page in reader.pages:
            try:
                texts.append(page.extract_text() or "")
            except Exception as e:
                logger.warning("Failed to extract text from a page: %s", e)
        return "\n\n".join(texts)
