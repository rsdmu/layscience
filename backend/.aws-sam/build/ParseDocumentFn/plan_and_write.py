"""
Enhanced summarization step for LayScience.

This module contains the logic for planning and writing lay summaries from
scientific documents.  It improves upon the original implementation by
externalising the system prompt via an environment variable (``LAYSCIENCE_SYSTEM_PROMPT``)
and by adding additional runtime safety around the LLM call and JSON parsing.

The default system prompt instructs the LLM to produce either a micro summary
(three concise sentences) or an extended summary (five paragraphs) for an
informed lay audience.  If you wish to customise the behaviour further,
set the ``LAYSCIENCE_SYSTEM_PROMPT`` environment variable.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from ..common.chunking import chunk_document
from ..common.retrieval import bm25_topk
from ..common.deepinfra import chat
from ..common.util import compute_readability, detect_disclaimers

# Read a custom system prompt from the environment.  This allows operators to
# tweak the summarisation behaviour without changing code.  See the default
# below for guidance on how to structure the prompt.
DEFAULT_SYSTEM_PROMPT: str = """
You are an expert scientific writer who specialises in translating technical
research papers into crisp, accurate summaries for an informed general audience.
Your tone is clear, neutral and engaging, avoiding jargon whenever possible.
Where specialist terminology is necessary you provide a concise definition.

You support two modes of operation:

• **micro** summaries consist of exactly three sentences.  The first sentence
  states the problem or question addressed by the research, the second summarises
  what the authors did and what they found, and the third explains why it
  matters or how the work might be applied.  Keep the entire micro summary
  under 200 words.

• **extended** summaries are five short paragraphs, clearly separated by blank
  lines.  The paragraphs cover: (1) background and context, (2) how the study
  was performed, (3) the principal findings, (4) the implications or
  significance of the work, and (5) limitations and future directions.

In both modes you must ground every claim in the provided evidence and cite the
source passages by their ``chunk_id`` in square brackets.  Never fabricate
information or statistics.  Maintain a lay reading level and use analogies only
to clarify concepts, never to embellish.  Output must be valid JSON as per the
schema described in the user prompt.
""".strip()

SYSTEM_PROMPT: str = os.environ.get("LAYSCIENCE_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT)

def build_user_prompt(mode: str, abstract: str, evidence: List[Dict[str, Any]]) -> str:
    """
    Build the user-facing portion of the prompt.

    :param mode: Either ``micro`` or ``extended``.
    :param abstract: The document abstract or the first portion of the text.
    :param evidence: A list of evidence chunks with ``id`` and ``text`` keys.
    :return: A multiline string to be sent as the user message.
    """
    evidence_str = "\n".join(
        [f"[{item['id']}] {item['text'][:800]}" for item in evidence]
    )
    rules = '''Output format (strict JSON):

{
  "mode": "micro" | "extended",
  "lay_summary": "...",
  "headline": "...",
  "keywords": ["...","..."],
  "jargon_definitions": { "term": "short plain explanation", "...": "..." },
  "sentences": [
    { "text": "first sentence", "citations": [chunk_id,...] }
  ]
}

Rules:
- Audience: informed layperson.
- Structure:
  - micro: exactly 3 sentences (Problem; What they did/found; Why it matters).
  - extended: 5 paragraphs (Background; How the study worked; What they found; Why it matters; Limits & next).
- Length: micro ≤ 200 words total; extended ≤ 5 short paragraphs; concise sentences.
- Veracity: only use facts supported by the provided evidence. Do not invent numbers.
- Jargon: keep minimal; if used, add one-line definition.
- Distinctiveness: be specific about this paper.
- Accessibility: analogies ok if clarifying, not replacing meaning.
- For each sentence, include citations as [chunk_id] from the evidence pool.
'''
    up = f'''Abstract & snippets:
"""{abstract[:4000]}"""

Relevant evidence pool (chunk_id → passage):
{evidence_str}

Requirements — produce the lay summary and auxiliary outputs exactly as described above.
Mode: {mode}
'''
    return rules + "\n" + up


def safe_json_parse(text: str) -> Dict[str, Any]:
    """
    Attempt to parse JSON returned by the LLM.  The model may occasionally
    prepend or append unrelated text.  We therefore extract the substring
    between the first '{' and last '}'.

    :param text: Raw string returned by the model.
    :return: Parsed JSON object.
    :raises ValueError: if valid JSON cannot be extracted.
    """
    try:
        return json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("LLM output did not contain JSON object")
        return json.loads(text[start : end + 1])


def handler(event: Dict[str, Any], context: Optional[Any]) -> Dict[str, Any]:
    """
    Main Lambda entry point for the plan-and-write step.

    :param event: A dictionary containing the document text and optional mode.
    :param context: Lambda context (unused).
    :return: An augmented event dictionary including chunks, draft summary,
             readability metrics and any detected disclaimers.
    """
    text: str = event["text"]
    mode: str = event.get("mode", "micro")

    # Split the document into overlapping chunks and compute the abstract
    chunks = chunk_document(text)
    abstract = text[:2000]

    # Retrieve the top-k evidence chunks using BM25
    evidence_chunks = [
        {"id": c.id, "text": c.text} for c in bm25_topk(chunks, abstract, k=6)
    ]

    # Build the messages for the LLM
    user_msg = {
        "role": "user",
        "content": build_user_prompt(mode, abstract, evidence_chunks),
    }
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        user_msg,
    ]

    # Call the model via the DeepInfra chat API
    try:
        response_content: str = chat(
            messages,
            temperature=0.2,
            max_tokens=1200,
        )
    except Exception as exc:
        # Surface a more descriptive error upstream
        raise RuntimeError(f"LLM call failed: {exc}") from exc

    # Parse the JSON draft returned by the model
    data: Dict[str, Any] = safe_json_parse(response_content)

    # Compute reading level and detect any health/finance/legal flags
    reading = compute_readability(data.get("lay_summary", ""))
    disclaimers = detect_disclaimers(abstract)

    return {
        **event,
        "chunks": [
            {
                "id": c.id,
                "page": c.page,
                "start": c.start,
                "end": c.end,
                "text": c.text,
            }
            for c in chunks
        ],
        "draft": data,
        "reading": reading,
        "disclaimers": disclaimers,
    }