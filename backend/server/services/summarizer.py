
import os
import logging
from typing import Dict

# optional import; if missing or MOCK_SUMMARIZER=1 we return mock results
logger = logging.getLogger("layscience.summarizer")

def summarise(text: str, mode: str = "micro") -> Dict:
    """
    Returns a dict with fields:
      - title
      - tl;dr
      - key_points: list[str]
      - limitations: list[str]
    """
    if os.getenv("MOCK_SUMMARIZER") == "1" or not os.getenv("OPENAI_API_KEY"):
        logger.warning("Using MOCK summariser (set OPENAI_API_KEY to enable real LLM)")
        if mode == "micro":
            return {
                "title": "Example summary (mock)",
                "tldr": "This is a mock micro-summary of the uploaded PDF.",
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

    # Real LLM call
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    system = (
        "You are an expert science communicator. Given the extracted text of a research paper, "
        "write a clear, accurate summary for a general but informed audience. "
        "Respond in JSON with keys: title (string), tldr (string), key_points (array of 3-6 strings), "
        "limitations (array of 2-4 strings)."
    )
    user = (
        f"Mode: {mode}\n"
        "If mode is 'micro', keep tldr under 200 words. If 'extended', provide more detail.\n\n"
        f"Paper text:\n{text[:16000]}"
    )
    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL","gpt-4o-mini"),
        messages=[{"role":"system","content":system},{"role":"user","content":user}],
        temperature=0.2,
        response_format={"type":"json_object"}
    )
    content = resp.choices[0].message.content
    import json
    data = json.loads(content)
    # minimal validation
    for k in ("title","tldr","key_points","limitations"):
        data.setdefault(k, "" if k in ("title","tldr") else [])
    return data
