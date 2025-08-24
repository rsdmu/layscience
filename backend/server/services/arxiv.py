"""Simple arXiv API client utilities.

Provides functions to search arXiv by title or keyword and to construct
PDF URLs for a given arXiv identifier.

The main helper :func:`search` performs a query against the arXiv API
and returns a normalised list of result dictionaries containing
``title``, ``authors``, ``id``, ``links``, ``published``, ``updated`` and
``categories`` fields.
"""

from __future__ import annotations

import html
import difflib
import httpx
import re
from typing import List, Dict, Any
from xml.etree import ElementTree as ET

API_URL = "https://export.arxiv.org/api/query"


def _parse_atom(xml_text: str) -> List[Dict[str, Any]]:
    """Parse an Atom XML string returned by arXiv.

    Parameters
    ----------
    xml_text:
        Raw Atom feed as returned by the arXiv API.

    Returns
    -------
    list of dict
        Normalised result dictionaries.
    """
    root = ET.fromstring(xml_text)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    results: List[Dict[str, Any]] = []
    for entry in root.findall("atom:entry", ns):
        # Extract basic fields
        raw_id = entry.findtext("atom:id", default="", namespaces=ns)
        arxiv_id = raw_id.rsplit("/", 1)[-1]
        title = entry.findtext("atom:title", default="", namespaces=ns)
        title = html.unescape(" ".join(title.split()))  # normalise whitespace
        # Strip simple LaTeX math delimiters (e.g. $r$)
        title = re.sub(r"\$(.+?)\$", r"\1", title).replace("$", "")
        published = entry.findtext("atom:published", default="", namespaces=ns)
        updated = entry.findtext("atom:updated", default="", namespaces=ns)

        # Authors
        authors = [
            a.findtext("atom:name", default="", namespaces=ns)
            for a in entry.findall("atom:author", ns)
        ]
        authors = [a for a in authors if a]

        # Links
        links: Dict[str, str] = {}
        for link in entry.findall("atom:link", ns):
            href = link.attrib.get("href")
            if not href:
                continue
            rel = link.attrib.get("rel")
            typ = link.attrib.get("type")
            if typ == "application/pdf" or href.lower().endswith(".pdf"):
                links["pdf"] = href
            elif rel == "alternate":
                links["html"] = href

        # Categories
        categories = [
            c.attrib.get("term")
            for c in entry.findall("atom:category", ns)
            if c.attrib.get("term")
        ]

        results.append(
            {
                "id": arxiv_id,
                "title": title,
                "authors": authors,
                "links": links,
                "published": published,
                "updated": updated,
                "categories": categories,
            }
        )
    return results


def search(query: str, max_results: int = 50) -> List[Dict[str, Any]]:
    """Search arXiv for ``query`` and return normalised, ranked results.

    The initial request asks arXiv for a larger pool of results which are then
    ranked locally by string similarity so that the closest matches appear
    first.  This helps surface the most relevant papers for fuzzy queries.

    Parameters
    ----------
    query:
        Search query to run against arXiv's API.  It is sent as
        ``search_query=all:<query>``.
    max_results:
        Maximum number of results to return after ranking (default 50).
    """
    # httpx will handle URL encoding of the query parameters for us, so we
    # pass the raw query string directly.  Fetch a larger pool than requested
    # to allow for local ranking.
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_results * 2,
    }
    r = httpx.get(API_URL, params=params, timeout=20.0)
    r.raise_for_status()
    results = _parse_atom(r.text)
    q = query.lower()
    results.sort(
        key=lambda x: difflib.SequenceMatcher(None, q, x["title"].lower()).ratio(),
        reverse=True,
    )
    return results[:max_results]


def pdf_url(arxiv_id: str) -> str:
    """Return the canonical PDF URL for ``arxiv_id``.

    Examples
    --------
    >>> pdf_url("1234.5678v1")
    'https://arxiv.org/pdf/1234.5678v1.pdf'
    """
    arxiv_id = arxiv_id.split("/")[-1]
    return f"https://arxiv.org/pdf/{arxiv_id}.pdf"
