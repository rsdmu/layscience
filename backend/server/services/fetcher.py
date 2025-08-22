import logging
import re
from typing import Tuple, Dict, Any

import httpx
from bs4 import BeautifulSoup

from .pdfio import extract_text_and_meta
from . import errors as err

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "LayScience/1.0 (+https://example.invalid)"}

DOI_RE = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Z0-9]+$", re.IGNORECASE)

def is_doi(s: str) -> bool:
    return bool(DOI_RE.match(s.strip()))

def fetch_and_extract(ref: str) -> Tuple[str, Dict[str, Any]]:
    """
    ref can be DOI or URL. If DOI, resolve via doi.org.
    If URL to HTML, try to find citation_pdf_url meta. If PDF, parse directly.
    """
    meta: Dict[str, Any] = {"input": ref}
    url = ref
    if is_doi(ref):
        url = f"https://doi.org/{ref}"
        meta["doi"] = ref

    try:
        with httpx.Client(follow_redirects=True, headers=HEADERS, timeout=httpx.Timeout(20.0)) as client:
            r = client.get(url)
            r.raise_for_status()
            ct = r.headers.get("content-type", "")
        # If PDF directly
            if "pdf" in ct.lower() or url.lower().endswith(".pdf"):
                # Save to tmp and parse
                import tempfile, os
                fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
                with os.fdopen(fd, "wb") as f:
                    f.write(r.content)
                text, pmeta = extract_text_and_meta(tmp_path)
                meta.update(pmeta)
                meta["source"] = "fetched_pdf"
                return text, meta

        # Else HTML – try to resolve a PDF
        html = r.text
        soup = BeautifulSoup(html, "html.parser")
        # Try common meta tags
        candidates = []
        for selector in [
            ("meta", {"name": "citation_pdf_url"}),
            ("meta", {"name": "dc.identifier.fulltext", "scheme":"dcterms.fulltext"}),
            ("a", {"href": True}),
        ]:
            for el in soup.find_all(*selector):
                href = el.get("content") or el.get("href")
                if not href:
                    continue
                if href.lower().endswith(".pdf") or "pdf" in href.lower():
                    candidates.append(href)
        # Normalize URLs
        from urllib.parse import urljoin
        for href in candidates:
            pdf_url = urljoin(r.url, href)
            try:
                pr = client.get(pdf_url)
                if pr.status_code == 200 and ("pdf" in pr.headers.get("content-type","").lower()):
                    import tempfile, os
                    fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
                    with os.fdopen(fd, "wb") as f:
                        f.write(pr.content)
                    text, pmeta = extract_text_and_meta(tmp_path)
                    meta.update(pmeta)
                    meta["source"] = "resolved_pdf"
                    meta["pdf_url"] = pdf_url
                    return text, meta
            except Exception:
                continue

        # Fallback: use HTML meta description/abstract
        title = soup.find("meta", {"name":"citation_title"}) or soup.find("title")
        if title:
            meta["title"] = title.get("content") if title.name == "meta" else title.text
        desc = soup.find("meta", {"name":"description"}) or soup.find("meta", {"property":"og:description"})
        text = ""
        if desc and (desc.get("content") or "").strip():
            text = desc.get("content").strip()
            meta["source"] = "html_meta"
            return text, meta

        # Final fallback: plain text from <p> elements
        paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
        text = "\n\n".join(paragraphs[:15]).strip()
        meta["source"] = "html_text"
        return text, meta
    except httpx.HTTPStatusError as e:
        logger.warning("HTTP error fetching %s: %s", url, e.response.status_code)
        raise err.UserFacingError(
            code="fetch_http_error",
            public_message=f"Could not fetch the paper (HTTP {e.response.status_code}).",
            where="fetch_and_extract",
            hint="Check the DOI/URL and try again.",
        ) from e
    except httpx.RequestError as e:
        logger.warning("Request error fetching %s: %s", url, e)
        raise err.UserFacingError(
            code="fetch_failed",
            public_message="Could not reach the paper URL/DOI.",
            where="fetch_and_extract",
            hint="Verify the link and your network connection.",
        ) from e
