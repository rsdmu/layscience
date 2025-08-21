
import os
from typing import Dict, Any

def translate_summary(summary: Dict[str, Any], target_language: str) -> Dict[str, Any]:
    """
    Translate the summary dict to the target language using OpenAI or return the same in mock.
    """
    if os.getenv("MOCK_SUMMARIZER") == "1" or not os.getenv("OPENAI_API_KEY"):
        # mock: just attach "[translated]" tag
        def tr(x):
            if isinstance(x, str):
                return f"[{target_language}] {x}"
            if isinstance(x, list):
                return [f"[{target_language}] {i}" for i in x]
            return x
        return {k: tr(v) for k, v in summary.items()}

    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    import json
    user = (
        f"Translate the following JSON into {target_language}. Keep the JSON structure identical, only translate values.\n"
        f"{json.dumps(summary)}"
    )
    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL","gpt-4o-mini"),
        messages=[{"role":"system","content":"Translate while preserving JSON structure."},
                  {"role":"user","content":user}],
        temperature=0.0,
        response_format={"type":"json_object"}
    )
    import json as _json
    return _json.loads(resp.choices[0].message.content)
