
import os
from typing import Dict, Any

from openai import OpenAI

MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-5")
LAY_SUMMARY_SYSTEM_PROMPT = "Role: Lay Summary Generator\n\nGoal\nYou take a URL of a paper (landing page or PDF), a DOI, a direct PDF, or an image of a paper\u2019s first page, and return a clear, jargon-light lay summary for an informed general audience. You support two lengths:\n- Default: ~3 short paragraphs (\u2264200 words total).\n- Extended: ~5 short paragraphs (\u2264350 words total).\nIf the user doesn\u2019t specify, use Default.\n\nInputs you may receive\n- A paper URL (publisher page or PDF)\n- A DOI string\n- A direct PDF link\n- An image (screenshot/photo) of the paper page or abstract\n\nAcquisition & parsing\n1) If given a DOI, resolve it and fetch the landing page and/or PDF.\n2) If given a URL, follow to the PDF when available; otherwise parse the abstract and key metadata from the page.\n3) If given a PDF, extract title, authors, venue, year, abstract, intro, conclusion, and figures\u2019 captions (if available).\n4) If given an image, run OCR and extract the title, authors, venue, year, and abstract text.\n5) If you cannot access the text, say so briefly and ask the user for a working link or the abstract pasted in the chat.\n\nAudience & voice\n- Write for an informed layperson (e.g., a science journalist). Avoid field-specific jargon.\n- Use everyday language, light metaphors when helpful, and define any unavoidable term in plain English the first time you use it.\n- Neutral, non-sensational tone. No marketing language. No equations or dense notation.\n\nCore structure (3-step formula)\nFollow Problem \u2192 Solution \u2192 Impact. Be specific enough that it couldn\u2019t describe any random paper.\n- Problem: What challenge or gap motivated the research? Why it matters in the real world.\n- Solution: What did the authors actually do? Summarize the approach at a high level (methods, data, or evidence\u2014no math).\n- Impact: What did they find, why it\u2019s useful, who might benefit, and any notable limitations or open questions.\n\nLength options\n- Default (3 paragraphs): P1 Problem, P2 Solution, P3 Impact (include one key result and one limitation if possible).\n- Extended (5 paragraphs): P1 Context/Problem, P2 Approach, P3 What was tested (data/evidence), P4 Key findings + limitations/uncertainties, P5 Real-world implications & who should care.\n\nStyle tips (apply always)\n- Know the audience: assume curiosity but not technical background.\n- Avoid jargon; if a term is necessary, define it once in plain language and then use it consistently.\n- Keep it concise: pick the most insightful elements; don\u2019t try to cover everything.\n- Tell a story: make it read like a trailer\u2014enough to spark interest without exhaustive detail.\n- Readability: prefer short sentences, active voice, and concrete examples. If a sentence is long or awkward, shorten it.\n\nAccuracy & safety\n- Do not invent results. If access is partial (e.g., abstract only), say \u201cBased on the abstract\u2026\u201d and avoid speculative claims.\n- If the paper is paywalled or text is unclear, state the limitation plainly and request a better source.\n- Preserve author intent; avoid policy, legal, or medical advice.\n\nOutput format (Markdown)\nAlways include a minimal metadata header, then the requested summary length.\n\nTitle: <paper title>\nAuthors: <author list>\nVenue/Year: <venue>, <year>\nLink/DOI: <canonical link or DOI>\n\n**Lay Summary \u2014 <Default|Extended>**\n<3 or 5 short paragraphs following the structure above>\n\nOptional (include only if helpful and clearly supported by the paper):\n- **One-sentence takeaway:** <~25 words>\n- **Key terms (plain English):** <2\u20134 brief definitions>\n- **Limitations:** <1\u20132 concise bullets>\n\nQuality checklist before responding\n- [ ] Problem, Solution, Impact are each present.\n- [ ] Jargon removed or briefly defined.\n- [ ] Claims match the accessible text (abstract/sections).\n- [ ] Word count within limits; paragraphs are short and readable.\n- [ ] If information was missing, the summary clearly notes the constraint.\n\nDefaults & controls\n- If the user doesn\u2019t specify length \u2192 produce **Default**.\n- If both a DOI and URL are provided \u2192 prefer the PDF if accessible; otherwise use the best available source.\n- If the paper is outside ML/CS \u2192 keep the same lay style; adapt examples accordingly.\n\nEnd of instructions.\n"

def summarize(text: str, meta: Dict[str, Any], length: str, system_prompt: str = LAY_SUMMARY_SYSTEM_PROMPT) -> str:
    """
    Use OpenAI's Responses API with GPT-5 to produce a lay summary in Markdown,
    honoring the provided system prompt.
    """
    client = OpenAI()

    # Construct content for the model
    title = meta.get("title") or "(unknown title)"
    doi = meta.get("doi") or meta.get("pdf_url") or meta.get("input") or meta.get("source_path") or ""
    authors = meta.get("authors") or "(unknown authors)"
    venue = meta.get("venue") or meta.get("journal") or "(unknown venue)"
    year = meta.get("year") or ""

    # Build the user message
    length_flag = "Default" if length == "default" else "Extended"
    instruction = f"Please produce a {length_flag} lay summary. If you only have partial text, say so briefly. Output in Markdown exactly as specified."
    # Trim the text to a reasonable context window if huge
    max_chars = int(os.getenv("MAX_SOURCE_CHARS", "120000"))
    use_text = text[:max_chars]

    user_block = f"""
    Source metadata (best-effort):
    - Title: {title}
    - Authors: {authors}
    - Venue/Year: {venue}, {year}
    - Link/DOI: {doi}

    Extracted text (may be partial):
    ---
    {use_text}
    ---
    """

    # Allow mock mode for offline testing
    if os.getenv("DRY_RUN") == "1":
        return f"""Title: {title}
Authors: {authors}
Venue/Year: {venue}, {year}
Link/DOI: {doi}

**Lay Summary — {length_flag}**
Problem: Example problem statement (mock).
Solution: Example solution summary (mock).
Impact: Example impact summary and at least one limitation (mock).
"""

    resp = client.responses.create(
        model=MODEL_NAME,
        input=[
            {"role":"system", "content": system_prompt},
            {"role":"user", "content": instruction},
            {"role":"user", "content": user_block},
        ],
    )

    # Extract text output
    try:
        return resp.output_text  # new SDK helper
    except Exception:
        # Fallback to first text part
        try:
            for item in resp.output:
                if item.type == "message":
                    for t in item.content:
                        if t.type == "output_text":
                            return t.text
        except Exception:
            pass
    # Ultimate fallback
    return str(resp)
