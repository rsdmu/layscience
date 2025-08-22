"""OpenAI summarisation helper.

Constructs a system prompt and calls the OpenAI Responses API to produce a
jargon‑light lay summary. Includes retries, model fallback, and better error
hints. Supports DRY_RUN=1 for offline testing.
"""

import logging
import os
import time
from typing import Dict, Any, List, Optional

from openai import OpenAI

from . import errors as err

# Primary + fallback models come from env
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-5")
FALLBACK_MODEL = os.getenv("OPENAI_FALLBACK_MODEL", "gpt-4o-mini")

# Tunables
MAX_SOURCE_CHARS = int(os.getenv("MAX_SOURCE_CHARS", "120000"))
MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", "900"))
TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))

logger = logging.getLogger(__name__)

# System prompt guiding the model to produce lay summaries
LAY_SUMMARY_SYSTEM_PROMPT = (
    "Role: Lay Summary Generator\n\n"
    "Goal\n"
    "You take a URL of a paper (landing page or PDF), a DOI, a direct PDF, or an image of a paper’s first page, and return a clear, jargon-light lay summary for an informed general audience.\n"
    "You support two lengths:\n"
    "- Default: ~3 short paragraphs (≤200 words total).\n"
    "- Extended: ~5 short paragraphs (≤350 words total).\n"
    "If the user doesn’t specify, use Default.\n\n"
    "Inputs you may receive\n"
    "- A paper URL (publisher page or PDF)\n"
    "- A DOI string\n"
    "- A direct PDF link\n"
    "- An image (screenshot/photo) of the paper page or abstract\n\n"
    "Acquisition & parsing\n"
    "1) If given a DOI, resolve it and fetch the landing page and/or PDF.\n"
    "2) If given a URL, follow to the PDF when available; otherwise parse the abstract and key metadata from the page.\n"
    "3) If given a PDF, extract title, authors, venue, year, abstract, intro, conclusion, and figures’ captions (if available).\n"
    "4) If given an image, run OCR and extract the title, authors, venue, year, and abstract text.\n"
    "5) If you cannot access the text, say so briefly and ask the user for a working link or the abstract pasted in the chat.\n\n"
    "Audience & voice\n"
    "- Write for an informed layperson (e.g., a science journalist). Avoid field-specific jargon.\n"
    "- Use everyday language, light metaphors when helpful, and define any unavoidable term in plain English the first time you use it.\n"
    "- Neutral, non-sensational tone. No marketing language. No equations or dense notation.\n\n"
    "Core structure (3-step formula)\n"
    "Follow Problem → Solution → Impact. Be specific enough that it couldn’t describe any random paper.\n"
    "- Problem: What challenge or gap motivated the research? Why it matters in the real world.\n"
    "- Solution: What did the authors actually do? Summarise the approach at a high level (methods, data, or evidence—no math).\n"
    "- Impact: What did they find, why it’s useful, who might benefit, and any notable limitations or open questions.\n\n"
    "Length options\n"
    "- Default (3 paragraphs): P1 Problem, P2 Solution, P3 Impact (include one key result and one limitation if possible).\n"
    "- Extended (5 paragraphs): P1 Context/Problem, P2 Approach, P3 What was tested (data/evidence), P4 Key findings + limitations/uncertainties, P5 Real-world implications & who should care.\n\n"
    "Style tips (apply always)\n"
    "- Know the audience: assume curiosity but not technical background.\n"
    "- Avoid jargon; if a term is necessary, define it once in plain language and then use it consistently.\n"
    "- Keep it concise: pick the most insightful elements; don’t try to cover everything.\n"
    "- Tell a story: make it read like a trailer—enough to spark interest without exhaustive detail.\n"
    "- Readability: prefer short sentences, active voice, and concrete examples. If a sentence is long or awkward, shorten it.\n\n"
    "Accuracy & safety\n"
    "- Do not invent results. If access is partial (e.g., abstract only), say “Based on the abstract…” and avoid speculative claims.\n"
    "- If the paper is paywalled or text is unclear, state the limitation plainly and request a better source.\n"
    "- Preserve author intent; avoid policy, legal, or medical advice.\n\n"
    "Output format (Markdown)\n"
    "Always include a minimal metadata header, then the requested summary length.\n\n"
    "Title: \n"
    "Authors: \n"
    "Venue/Year: , \n"
    "Link/DOI: \n\n"
    "**Lay Summary — **\n"
    "<3 or 5 short paragraphs following the structure above>\n\n"
    "Optional (include only if helpful and clearly supported by the paper):\n"
    "- **One-sentence takeaway:** <~25 words>\n"
    "- **Key terms (plain English):** <2–4 brief definitions>\n"
    "- **Limitations:** <1–2 concise bullets>\n\n"
    "Quality checklist before responding\n"
    "- [ ] Problem, Solution, Impact are each present.\n"
    "- [ ] Jargon removed or briefly defined.\n"
    "- [ ] Claims match the accessible text (abstract/sections).\n"
    "- [ ] Word count within limits; paragraphs are short and readable.\n"
    "- [ ] If information was missing, the summary clearly notes the constraint.\n\n"
    "Defaults & controls\n"
    "- If the user doesn’t specify length → produce **Default**.\n"
    "- If both a DOI and URL are provided → prefer the PDF if accessible; otherwise use the best available source.\n"
    "- If the paper is outside ML/CS → keep the same lay style; adapt examples accordingly.\n\n"
    "End of instructions.\n"
)


def _error_hint(exc: Exception) -> str:
    """Best-effort classification → human-friendly hint."""
    name = exc.__class__.__name__
    msg = str(exc)
    status = getattr(exc, "status_code", None)

    if status in (401, 403) or "Authentication" in name:
        return "OpenAI auth/entitlement issue. Verify OPENAI_API_KEY and that the model is available to your account."
    if status == 429 or "RateLimit" in name:
        return "Rate limited by OpenAI. Retry with backoff or reduce concurrency."
    if status in (400, 413) or "context length" in msg.lower() or "too large" in msg.lower():
        return "Payload too large. Lower MAX_SOURCE_CHARS or use a shorter source (e.g., abstract page)."
    return "Transient network/service error. Retry later or check Render logs for details."


def summarise(text: str, meta: Dict[str, Any], length: str,
              system_prompt: str = LAY_SUMMARY_SYSTEM_PROMPT) -> str:
    """Produce a lay summary using OpenAI’s Responses API."""
    title = meta.get("title") or "(unknown title)"
    doi = meta.get("doi") or meta.get("pdf_url") or meta.get("input") or meta.get("source_path") or ""
    authors = meta.get("authors") or "(unknown authors)"
    venue = meta.get("venue") or meta.get("journal") or "(unknown venue)"
    year = meta.get("year") or ""

    length_flag = "Default" if length == "default" else "Extended"
    instruction = (
        f"Please produce a {length_flag} lay summary. If you only have partial text, "
        f"say so briefly. Output in Markdown exactly as specified."
    )

    # Trim large sources defensively
    use_text = (text or "")[:MAX_SOURCE_CHARS]
    logger.debug("Summariser: using %d chars of source (max=%d)", len(use_text), MAX_SOURCE_CHARS)

    user_block = f"""
Source metadata (best‑effort):
- Title: {title}
- Authors: {authors}
- Venue/Year: {venue}, {year}
- Link/DOI: {doi}

Extracted text (may be partial):
---
{use_text}
---
"""

    # Offline mock
    if os.getenv("DRY_RUN") == "1":
        return (
            f"Title: {title}\n"
            f"Authors: {authors}\n"
            f"Venue/Year: {venue}, {year}\n"
            f"Link/DOI: {doi}\n\n"
            f"**Lay Summary — {length_flag}**\n"
            f"Problem: Example problem statement (mock).\n\n"
            f"Solution: Example solution summary (mock).\n\n"
            f"Impact: Example impact summary and at least one limitation (mock).\n"
        )

    client = OpenAI()

    # Build chat-style messages for the Responses API
    def _build_messages() -> List[Dict[str, str]]:
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": instruction},
            {"role": "user", "content": user_block},
        ]

    models_to_try: List[str] = [MODEL_NAME]
    if FALLBACK_MODEL and FALLBACK_MODEL != MODEL_NAME:
        models_to_try.append(FALLBACK_MODEL)

    last_exc: Optional[Exception] = None
    response = None

    for model in models_to_try:
        for attempt in range(3):
            try:
                logger.info("Calling OpenAI model=%s attempt=%d", model, attempt + 1)
                response = client.responses.create(
                    model=model,
                    messages=_build_messages(),
                    temperature=TEMPERATURE,
                    max_output_tokens=MAX_OUTPUT_TOKENS,
                )
                last_exc = None
                break
            except Exception as e:  # network/auth/rate-limit/size/etc.
                last_exc = e
                # If the model looks invalid, try the next model immediately
                msg = str(e).lower()
                invalid_model = ("model" in msg and "not found" in msg) or ("unsupported" in msg)
                if invalid_model and model != models_to_try[-1]:
                    logger.warning("Model '%s' rejected request; trying fallback. Error: %s", model, e)
                    break
                # backoff and retry
                delay = 1.5 * (attempt + 1)
                logger.warning("OpenAI call failed (attempt %d): %s; retrying in %.1fs", attempt + 1, e, delay)
                time.sleep(delay)
        if response is not None:
            break

    if last_exc is not None:
        hint = _error_hint(last_exc)
        logger.error("OpenAI request failed after retries: %s", last_exc)
        raise err.UserFacingError(
            code="llm_error",
            public_message="Failed to generate summary.",
            where="summarise",
            hint=hint,
        ) from last_exc

    # Extract text output
    try:
        return response.output_text  # SDK convenience
    except Exception:
        # Fallback to first text part
        try:
            for item in getattr(response, "output", []):
                if getattr(item, "type", None) == "message":
                    for t in getattr(item, "content", []):
                        if getattr(t, "type", None) == "output_text":
                            return getattr(t, "text", "")
        except Exception:
            pass

    # Ultimate fallback
    return str(response)
