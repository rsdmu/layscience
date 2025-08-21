import json
from ..common.chunking import chunk_document
from ..common.retrieval import bm25_topk
from ..common.deepinfra import chat
from ..common.util import compute_readability, detect_disclaimers

SYSTEM_PROMPT = "You are a helpful assistant that converts technical abstracts and passages into lay summaries for an informed general audience (science journalists, policymakers, interested non-specialists). Make the paper understandable, accurate, and concise. Avoid jargon unless strictly necessary."

def build_user_prompt(mode: str, abstract: str, evidence: list):
    evidence_str = "\n".join([f"[{i['id']}] {i['text'][:800]}" for i in evidence])
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
  - micro: exactly 3 sentences (Problem, What they did/found, Why it matters).
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

def handler(event, context):
    text = event["text"]
    mode = event.get("mode","micro")
    chunks = chunk_document(text)
    abstract = text[:2000]
    ev = [ {"id": c.id, "text": c.text} for c in bm25_topk(chunks, abstract, k=6) ]
    user = {"role":"user","content": build_user_prompt(mode, abstract, ev)}
    content = chat([{"role":"system","content": SYSTEM_PROMPT}, user], temperature=0.2, max_tokens=1200)
    try:
        data = json.loads(content)
    except Exception:
        start = content.find("{"); end = content.rfind("}")
        data = json.loads(content[start:end+1])
    reading = compute_readability(data.get("lay_summary",""))
    disclaimers = detect_disclaimers(abstract)
    return { **event, "chunks": [ {"id": c.id, "page": c.page, "start": c.start, "end": c.end, "text": c.text} for c in chunks], "draft": data, "reading": reading, "disclaimers": disclaimers }
