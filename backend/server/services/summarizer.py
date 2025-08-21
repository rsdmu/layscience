"""
Advanced summariser for LayScience.

This module wraps the OpenAI API to produce lay summaries of scientific
papers using GPT‑5 (or another model specified via ``OPENAI_MODEL``).
It follows a detailed system prompt tailored for an informed general
audience and supports two summary lengths: micro (~200 words) and
extended (~350 words).  The output is returned as a JSON object with
four keys: ``title``, ``tldr``, ``key_points``, and ``limitations``.

If no OpenAI API key is provided or ``MOCK_SUMMARIZER=1`` is set,
mock summaries are returned for ease of development.
"""
import os
import logging
from typing import Dict

logger = logging.getLogger("layscience.summarizer")

def summarise(text: str, mode: str = "micro") -> Dict:
    """Summarise a paper's text into a layperson‑friendly JSON structure.

    Args:
        text: The extracted text of the paper (e.g. abstract, intro, etc.).
        mode: Either ``micro`` for ~200 word summaries or ``extended`` for
            ~350 word summaries.  Any other value defaults to ``micro``.

    Returns:
        A dict with keys ``title``, ``tldr``, ``key_points``, and
        ``limitations``.  ``key_points`` and ``limitations`` are lists of
        strings.  ``tldr`` is a single string containing the lay summary.

    Raises:
        Exception: If the OpenAI API call fails (network error, invalid
        key, etc.).  The caller should catch exceptions and handle
        them appropriately.
    """
    mode = mode.lower() if mode else "micro"
    if os.getenv("MOCK_SUMMARIZER") == "1" or not os.getenv("OPENAI_API_KEY"):
        logger.warning("Using MOCK summariser (set OPENAI_API_KEY to enable real LLM)")
        # Simple static mock output to aid development and UI testing
        if mode == "micro":
            return {
                "title": "Example summary (mock)",
                "tldr": "This is a mock micro‑summary of the uploaded PDF.",
                "key_points": [
                    "Key point 1 extracted from the paper.",
                    "Key point 2 summarising methods and findings.",
                    "Why it matters for a lay reader."
                ],
                "limitations": [
                    "Automated summaries can miss nuance.",
                    "Verify claims with the source."
                ]
            }
        else:
            return {
                "title": "Example extended summary (mock)",
                "tldr": "An extended overview of the paper, generated in mock mode.",
                "key_points": [
                    "Background and motivation.",
                    "Methods used and main results.",
                    "Implications, applications, and uncertainties."
                ],
                "limitations": [
                    "Mock output for development.",
                    "Provide an OPENAI_API_KEY to enable real summaries."
                ]
            }

    # Prepare the system prompt based on the user‑provided instructions.
    system_prompt = (
        "Role: Lay Summary Generator\n\n"
        "Goal\n"
        "You take a URL of a paper (landing page or PDF), a DOI, a direct PDF,"
        " or an image of a paper’s first page, and return a clear, jargon‑light"
        " lay summary for an informed general audience. You support two lengths:\n"
        "- Default: ~3 short paragraphs (≤200 words total).\n"
        "- Extended: ~5 short paragraphs (≤350 words total).\n"
        "If the user doesn’t specify, use Default.\n\n"
        "Audience & voice\n"
        "Write for an informed layperson (e.g., a science journalist). Avoid field‑specific jargon.\n"
        "Use everyday language, light metaphors when helpful, and define any unavoidable term in plain English the first time you use it.\n"
        "Neutral, non‑sensational tone. No marketing language. No equations or dense notation.\n\n"
        "Core structure (3‑step formula)\n"
        "Follow Problem → Solution → Impact. Be specific enough that it couldn’t describe any random paper.\n"
        "- Problem: What challenge or gap motivated the research? Why it matters in the real world.\n"
        "- Solution: What did the authors actually do? Summarise the approach at a high level (methods, data, or evidence—no math).\n"
        "- Impact: What did they find, why it’s useful, who might benefit, and any notable limitations or open questions.\n\n"
        "Length options\n"
        "- Default (3 paragraphs): P1 Problem, P2 Solution, P3 Impact (include one key result and one limitation if possible).\n"
        "- Extended (5 paragraphs): P1 Context/Problem, P2 Approach, P3 What was tested (data/evidence), P4 Key findings + limitations/uncertainties, P5 Real‑world implications & who should care.\n\n"
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
        "Output format (JSON)\n"
        "Respond in JSON with keys: title (string), tldr (string), key_points (array of 3-6 strings), limitations (array of 2-4 strings)."
    )

    # Truncate the input text to a reasonable length (up to 16k characters).  GPT‑5
    # supports larger contexts but we limit to reduce latency and cost.
    max_chars = 16000
    truncated_text = text[:max_chars]

    user_prompt = (
        f"Mode: {mode}\n"
        "Generate a lay summary for the provided paper text following the above instructions.\n"
        "Paper text:\n"
        f"{truncated_text}"
    )

    # Call the OpenAI API.  We set a low temperature to favour
    # reproducibility.  The model name defaults to gpt‑5 if not
    # provided.  Use JSON response format so we can parse it easily.
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    try:
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-5"),
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
    except Exception as e:
        # Re‑raise with context to aid debugging
        logger.exception("OpenAI summarisation call failed")
        raise
    content = resp.choices[0].message.content
    import json
    try:
        data = json.loads(content)
    except Exception:
        logger.error("Failed to parse LLM JSON response: %s", content)
        raise
    # Ensure required keys exist
    for key in ("title", "tldr", "key_points", "limitations"):
        data.setdefault(key, "" if key in ("title", "tldr") else [])
    return data