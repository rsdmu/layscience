import os, json, base64
import boto3, requests

_secrets = boto3.client("secretsmanager")
_SECRET_ARN = os.environ.get("DEEPINFRA_SECRET_ARN") or os.environ.get("DEEPINFRA_API_KEY")

def _get_key() -> str:
    if _SECRET_ARN and _SECRET_ARN.startswith("arn:aws:secretsmanager"):
        val = _secrets.get_secret_value(SecretId=_SECRET_ARN)
        sec = val.get("SecretString") or base64.b64decode(val["SecretBinary"]).decode()
        data = json.loads(sec) if sec.strip().startswith("{") else {"DEEPINFRA_API_KEY": sec}
        return data.get("DEEPINFRA_API_KEY") or data.get("api_key")
    return _SECRET_ARN

def chat(messages, model=None, temperature=0.2, max_tokens=800):
    api_key = _get_key()
    model = model or os.environ.get("DEEPINFRA_CHAT_MODEL", "openai/gpt-oss-120b")
    url = "https://api.deepinfra.com/v1/openai/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    r = requests.post(url, headers=headers, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def entailment_check(evidence: str, claim: str) -> str:
    system = {"role":"system","content":"You are a careful scientific fact checker. Answer strictly YES or NO."}
    user = {"role":"user","content":f"Evidence:\n\"\"\"\n{evidence}\n\"\"\"\nClaim:\n\"{claim}\"\nDoes the evidence fully entail the claim? Answer YES or NO only."}
    out = chat([system, user], temperature=0.0, max_tokens=2)
    return out.strip().split()[0].upper()
