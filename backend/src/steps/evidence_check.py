from ..common.deepinfra import entailment_check, chat

def handler(event, context):
    chunks_map = { c["id"]: c for c in event["chunks"] }
    draft = event["draft"]
    fixed_sentences = []
    for s in draft.get("sentences", []):
        txt = s["text"].strip()
        ev_text = "\n".join([chunks_map[i]["text"] for i in s.get("citations", []) if i in chunks_map])
        verdict = entailment_check(ev_text, txt)
        if verdict == "YES":
            fixed_sentences.append(s)
        else:
            prompt = [
                {"role":"system","content":"Rewrite the claim to be fully supported by the evidence. Keep it short and accurate."},
                {"role":"user","content":f"Evidence:\n{ev_text}\n\nClaim:\n{txt}\n\nRewrite:"}
            ]
            new_txt = chat(prompt, temperature=0.1, max_tokens=120)
            fixed_sentences.append({**s, "text": new_txt.strip()})
    draft["sentences"] = fixed_sentences
    if draft.get("mode") == "micro":
        draft["lay_summary"] = " ".join([s["text"].strip() for s in fixed_sentences])[:1200]
    return { **event, "checked": draft }
