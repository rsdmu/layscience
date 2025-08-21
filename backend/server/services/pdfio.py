"""
Improved PDF IO utilities for LayScience.

This module handles DOI resolution, PDF downloading, and text extraction.
It uses a dedicated temporary directory under ``/tmp`` for storing
intermediate PDFs.  If the default temporary directory is not
writable, it will raise a clear error.  It logs operations using the
standard ``logging`` module.
"""
import os
import io
import re
import logging
import tempfile
from typing import Optional
import requests
from pypdf import PdfReader

logger = logging.getLogger("layscience.pdfio")

USER_AGENT = "LayScience/2.0 (+https://example.com)"


def resolve_doi_to_pdf_url(doi: str) -> str:
    """Resolve a DOI to a direct PDF URL or fallback page.

    If a DOI resolves directly to a PDF (via the Accept header), the
    content is downloaded and stored as a temporary file.  Otherwise we
    return the final URL so the caller can fetch the PDF or HTML page.
    """
    doi = doi.strip()
    if doi.lower().startswith("http"):
        return doi
    url = f"https://doi.org/{doi}"
    logger.info("Resolving DOI: %s", doi)
    r = requests.get(url, headers={"Accept": "application/pdf", "User-Agent": USER_AGENT}, allow_redirects=True, timeout=30)
    if r.status_code >= 400:
        raise RuntimeError(f"DOI resolution failed with status {r.status_code}")
    content_type = r.headers.get("Content-Type", "")
    if "application/pdf" in content_type.lower() and r.content:
        # We downloaded a PDF directly
        return _save_bytes(r.content)
    final_url = r.url
    if final_url.lower().endswith(".pdf"):
        return final_url
    # heuristics for common patterns
    if "nature.com" in final_url and "/pdf" not in final_url and not final_url.endswith(".pdf"):
        return final_url.rstrip("/") + ".pdf"
    return final_url


def fetch_pdf_from_url(url: str) -> str:
    """Download a PDF from a URL or copy a local file path."""
    if url.lower().startswith("http"):
        logger.info("Fetching PDF from %s", url)
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, allow_redirects=True, timeout=60)
        if r.status_code >= 400:
            raise RuntimeError(f"Failed to download PDF: HTTP {r.status_code}")
        ct = r.headers.get("Content-Type", "").lower()
        if "application/pdf" not in ct and not url.lower().endswith(".pdf"):
            # attempt to find a PDF link in the HTML
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
    """Persist bytes to a temporary PDF file and return its path."""
    tmp_dir = tempfile.gettempdir()
    # ensure directory exists and is writable
    if not os.access(tmp_dir, os.W_OK):
        raise RuntimeError(f"Temporary directory {tmp_dir} is not writable")
    import uuid
    path = os.path.join(tmp_dir, f"{uuid.uuid4().hex}.pdf")
    with open(path, "wb") as f:
        f.write(content)
    return path


def extract_text(path: str) -> str:
    """Extract text from a PDF using pypdf.

    We iterate through pages and concatenate the extracted text.  Any
    page that fails to extract text is logged and skipped.
    """
    logger.info("Extracting text from %s", path)
    with open(path, "rb") as f:
        reader = PdfReader(f)
        texts = []
        for i, page in enumerate(reader.pages):
            try:
                texts.append(page.extract_text() or "")
            except Exception as e:
                logger.warning("Failed to extract text from page %d: %s", i, e)
        return "\n\n".join(texts)