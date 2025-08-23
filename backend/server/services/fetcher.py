"""Utilities for fetching text from DOIs or URLs.

The ``fetch_and_extract`` function takes a DOI or URL and attempts to return
a tuple of (text, metadata).  If a DOI is provided it is resolved via
``https://doi.org/{doi}``.  If a PDF is encountered the file is downloaded
to a temporary file and parsed via ``pdfio``.  Otherwise it scrapes the
landing page to find a PDF link or falls back to meta tags and the first
paragraphs of the HTML.
"""

import logging
import os
import re
import tempfile
from typing import Tuple, Dict, Any, List

import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from .pdfio import extract_text_and_meta
from . import errors as err

logger = logging.getLogger(__name__)

# Request headers
# Use a mainstream browser user-agent to avoid 403s from sites that block
# unknown clients.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/pdf;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

DOI_RE = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Z0-9]+$", re.IGNORECASE)


def is_doi(s: str) -> bool:
    """Return True if the string looks like a DOI."""
    return bool(DOI_RE.match((s or "").strip()))


def _save_pdf_bytes(content: bytes) -> str:
    """Write PDF bytes to a temp file and return its path."""
    f = tempfile.NamedTemporaryFile(mode="wb", suffix=".pdf", delete=False)
    try:
        f.write(content or b"")
        return f.name
    finally:
        f.close()


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
        timeout = httpx.Timeout(20.0)
        # Keep r and client alive together
        with httpx.Client(follow_redirects=True, headers=HEADERS, timeout=timeout) as client:
            r = client.get(url)
            r.raise_for_status()

            final_url = str(r.url)  # httpx.URL -> str for urljoin
            ct = (r.headers.get("content-type") or "").lower()

            logger.debug("fetch_and_extract: final_url=%s (type=%s) ct=%s", final_url, type(final_url).__name__, ct)

            # Direct PDF response
            if "pdf" in ct or final_url.lower().endswith(".pdf"):
                tmp_path = _save_pdf_bytes(r.content)
                try:
                    text, pmeta = extract_text_and_meta(tmp_path)
                finally:
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass
                meta.update(pmeta)
                meta["source"] = "fetched_pdf"
                return text, meta

            # Otherwise parse HTML
            html = r.text
            soup = BeautifulSoup(html, "html.parser")
            base_url = final_url

            # Collect candidate PDF links from meta/link/a tags
            candidates: List[str] = []

            # Common meta + link hints
            for selector in [
                ("meta", {"name": "citation_pdf_url"}),
                ("meta", {"name": "dc.identifier.fulltext", "scheme": "dcterms.fulltext"}),
                ("link", {"rel": True, "type": "application/pdf"}),
            ]:
                for el in soup.find_all(*selector):
                    href = el.get("content") or el.get("href")
                    if href:
                        candidates.append(href)

            # Anchor tags
            for a in soup.find_all("a", href=True):
                candidates.append(a["href"])

            # Sanitise / filter candidates
            seen = set()
            cleaned: List[str] = []
            for href in candidates:
                # normalise type
                if isinstance(href, bytes):
                    try:
                        href = href.decode("utf-8", "ignore")
                    except Exception:
                        continue
                href = str(href).strip()
                if not href or href in seen:
                    continue
                seen.add(href)
                low = href.lower()
                # skip non-navigational schemes
                if low.startswith(("javascript:", "mailto:", "tel:", "data:")):
                    continue
                # prefer obvious PDF URLs
                if low.endswith(".pdf") or "pdf" in low:
                    cleaned.append(href)

            logger.debug("fetch_and_extract: %d candidate PDF hrefs after filtering", len(cleaned))

            # Try candidate PDFs
            for href in cleaned:
                pdf_url = urljoin(base_url, href)  # both args are str
                try:
                    pr = client.get(pdf_url)
                    if pr.status_code == 200 and "pdf" in (pr.headers.get("content-type", "").lower()):
                        tmp_path = _save_pdf_bytes(pr.content)
                        try:
                            text, pmeta = extract_text_and_meta(tmp_path)
                        finally:
                            try:
                                os.remove(tmp_path)
                            except Exception:
                                pass
                        meta.update(pmeta)
                        meta["source"] = "resolved_pdf"
                        meta["pdf_url"] = pdf_url
                        return text, meta
                except httpx.RequestError as e:
                    logger.debug("PDF candidate fetch failed %s: %s", pdf_url, e)
                    continue

            # Fallbacks: meta description / og:description
            title_el = soup.find("meta", {"name": "citation_title"}) or soup.find("title")
            if title_el:
                meta["title"] = title_el.get("content") if title_el.name == "meta" else title_el.text

            desc_el = soup.find("meta", {"name": "description"}) or soup.find(
                "meta", {"property": "og:description"}
            )
            if desc_el and (desc_el.get("content") or "").strip():
                text = desc_el.get("content").strip()
                meta["source"] = "html_meta"
                return text, meta

            # Final fallback: first paragraphs
            paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
            text = "\n\n".join([p for p in paragraphs if p][:15]).strip()
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
