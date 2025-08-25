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
from . import summries

# Primary + fallback models come from env
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-5")
FALLBACK_MODEL = os.getenv("OPENAI_FALLBACK_MODEL", "gpt-4o-mini")

# Tunables
MAX_SOURCE_CHARS = int(os.getenv("MAX_SOURCE_CHARS", "120000"))
MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", "900"))
TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))
OPENAI_TIMEOUT = float(os.getenv("OPENAI_TIMEOUT", "60"))

logger = logging.getLogger(__name__)

# Import mode-specific system prompts
LAY_SUMMARY_SYSTEM_PROMPT_DEFAULT = summries.LAY_SUMMARY_SYSTEM_PROMPT_DEFAULT
LAY_SUMMARY_SYSTEM_PROMPT_DETAILED = summries.LAY_SUMMARY_SYSTEM_PROMPT_DETAILED
LAY_SUMMARY_SYSTEM_PROMPT_FUNNY = summries.LAY_SUMMARY_SYSTEM_PROMPT_FUNNY

# Backwards compatibility for older imports
LAY_SUMMARY_SYSTEM_PROMPT = LAY_SUMMARY_SYSTEM_PROMPT_DEFAULT


def _error_hint(exc: Exception) -> str:
    """Best-effort classification → human-friendly hint."""
    name = exc.__class__.__name__
    msg = str(exc)
    status = getattr(exc, "status_code", None)
    low = msg.lower()

    if status in (401, 403) or "auth" in low:
        return "OpenAI auth/entitlement issue. Verify OPENAI_API_KEY and that the model is available to your account."
    if status == 429 or "rate" in low:
        return "Rate limited by OpenAI. Retry with backoff or reduce concurrency."
    if status in (400, 413) or "context" in low or "too large" in low or "max tokens" in low:
        return "Payload too large. Lower MAX_SOURCE_CHARS or use a shorter source (e.g., abstract page)."
    if "timeout" in low:
        return "OpenAI request timed out. Increase OPENAI_TIMEOUT or retry."
    return "Transient network/service error. Retry later or check Render logs for details."


def summarise(
    text: str,
    meta: Dict[str, Any],
    length: str,
    system_prompt: str = LAY_SUMMARY_SYSTEM_PROMPT,
) -> str:
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
    # Set per-request timeout via with_options so we don't rely on global client config
    responses_api = client.with_options(timeout=OPENAI_TIMEOUT).responses

    # Build Responses API input (NOT `messages`)
    def _build_input() -> List[Dict[str, str]]:
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
                response = responses_api.create(
                    model=model,
                    input=_build_input(),
                    temperature=TEMPERATURE,
                    max_output_tokens=MAX_OUTPUT_TOKENS,
                )
                last_exc = None
                break
            except Exception as e:  # network/auth/rate-limit/size/etc.
                last_exc = e
                low = str(e).lower()
                # If the model looks invalid, try the next model immediately
                invalid_model = ("model" in low and "not found" in low) or ("unsupported" in low)
                if invalid_model and model != models_to_try[-1]:
                    logger.warning("Model '%s' invalid; switching to fallback. Error: %s", model, e)
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
