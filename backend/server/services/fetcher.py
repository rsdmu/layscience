"""Utilities for fetching text from DOIs or URLs.

The ``fetch_and_extract`` function takes a DOI or URL and attempts to return
a tuple of (text, metadata).  If a DOI is provided it is resolved via
``https://doi.org/{doi}``.  If a PDF is encountered the file is downloaded
to a temporary file and parsed via ``pdfio``.  Otherwise it scrapes the
landing page to find a PDF link or falls back to meta tags and the first
paragraphs of the HTML.
"""

import logging
import re
from typing import Tuple, Dict, Any

import httpx
from bs4 import BeautifulSoup

from .pdfio import extract_text_and_meta
from . import errors as err


logger = logging.getLogger(__name__)

# User agent for HTTP requests
HEADERS = {"User-Agent": "LayScience/1.0 (+https://example.invalid)"}

DOI_RE = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Z0-9]+$", re.IGNORECASE)


def is_doi(s: str) -> bool:
    """Return True if the string looks like a DOI."""
    return bool(DOI_RE.match(s.strip()))


def fetch_and_extract(ref: str) -> Tuple[str, Dict[str, Any]]:
    """
    Resolve a DOI or fetch a URL and extract text/metadata.

    * If ``ref`` is a DOI, it is resolved via ``https://doi.org/<doi>``.
    * If the response is a PDF, the file is downloaded and parsed.
    * If the response is HTML, common meta tags are searched for a PDF link.
      If a PDF link is found it is downloaded and parsed.
      Otherwise the page’s meta description or the first few paragraphs are used.
    Raises ``UserFacingError`` on HTTP or connection errors.
    """
    meta: Dict[str, Any] = {"input": ref}
    url: str = ref
    if is_doi(ref):
        url = f"https://doi.org/{ref}"
        meta["doi"] = ref

    try:
        with httpx.Client(follow_redirects=True, headers=HEADERS, timeout=httpx.Timeout(20.0)) as client:
            r = client.get(url)
            r.raise_for_status()
            ct = r.headers.get("content-type", "")
            # If the resolved URL is a PDF, download and parse it
            if "pdf" in ct.lower() or url.lower().endswith(".pdf"):
                import tempfile
                fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
                # write the PDF bytes to the temporary file
                with open(tmp_path, "wb") as fobj:
                    fobj.write(r.content)
                text, pmeta = extract_text_and_meta(tmp_path)
                meta.update(pmeta)
                meta["source"] = "fetched_pdf"
                return text, meta

        # Otherwise treat as HTML
        html = r.text
        soup = BeautifulSoup(html, "html.parser")
        # Look for common PDF meta tags or links
        candidates = []
        for selector in [
            ("meta", {"name": "citation_pdf_url"}),
            ("meta", {"name": "dc.identifier.fulltext", "scheme": "dcterms.fulltext"}),
            ("a", {"href": True}),
        ]:
            for el in soup.find_all(*selector):
                href = el.get("content") or el.get("href")
                if not href:
                    continue
                if href.lower().endswith(".pdf") or "pdf" in href.lower():
                    candidates.append(href)
        # Attempt to download candidate PDFs
        from urllib.parse import urljoin
        for href in candidates:
            pdf_url = urljoin(r.url, href)
            try:
                pr = client.get(pdf_url)
                if pr.status_code == 200 and ("pdf" in pr.headers.get("content-type", "").lower()):
                    import tempfile
                    fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
                    with open(tmp_path, "wb") as fobj:
                        fobj.write(pr.content)
                    text, pmeta = extract_text_and_meta(tmp_path)
                    meta.update(pmeta)
                    meta["source"] = "resolved_pdf"
                    meta["pdf_url"] = pdf_url
                    return text, meta
            except Exception:
                continue

        # Fallback: use HTML meta description/abstract
        title_el = soup.find("meta", {"name": "citation_title"}) or soup.find("title")
        if title_el:
            meta["title"] = title_el.get("content") if title_el.name == "meta" else title_el.text
        desc_el = soup.find("meta", {"name": "description"}) or soup.find("meta", {"property": "og:description"})
        text = ""
        if desc_el and (desc_el.get("content") or "").strip():
            text = desc_el.get("content").strip()
            meta["source"] = "html_meta"
            return text, meta

        # Final fallback: extract first paragraphs
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