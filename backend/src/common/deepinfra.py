import os
import json
import base64
import logging
from typing import Any, Dict, List

import boto3
import requests

logger = logging.getLogger(__name__)

_secrets = boto3.client("secretsmanager")
_SECRET_ARN = os.environ.get("DEEPINFRA_SECRET_ARN") or os.environ.get("DEEPINFRA_API_KEY")


def _get_key() -> str:
    """
    Resolve the API key for the DeepInfra service.

    The key can be supplied directly via ``DEEPINFRA_API_KEY`` or via a Secrets
    Manager ARN in ``DEEPINFRA_SECRET_ARN``.  When using Secrets Manager the
    secret can either be a plain string (the API key) or a JSON object
    containing ``DEEPINFRA_API_KEY`` or ``api_key``.

    :return: The API key string.
    """
    if _SECRET_ARN and _SECRET_ARN.startswith("arn:aws:secretsmanager"):
        val = _secrets.get_secret_value(SecretId=_SECRET_ARN)
        sec = val.get("SecretString") or base64.b64decode(val["SecretBinary"]).decode()
        data = json.loads(sec) if sec.strip().startswith("{") else {"DEEPINFRA_API_KEY": sec}
        return data.get("DEEPINFRA_API_KEY") or data.get("api_key")
    return _SECRET_ARN or ""


def chat(
    messages: List[Dict[str, Any]],
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 800,
) -> str:
    """
    Send a chat completion request to the DeepInfra API.

    :param messages: A list of message dictionaries conforming to the OpenAI schema.
    :param model: Optional model name.  Defaults to the environment variable
        ``DEEPINFRA_CHAT_MODEL`` or ``openai/gpt-oss-120b``.
    :param temperature: Sampling temperature for the model.
    :param max_tokens: Maximum number of tokens to generate.
    :return: The assistant's message content.
    :raises RuntimeError: If the HTTP request fails or the response is malformed.
    """
    api_key = _get_key()
    model = model or os.environ.get("DEEPINFRA_CHAT_MODEL", "openai/gpt-oss-120b")
    url = "https://api.deepinfra.com/v1/openai/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error("DeepInfra API request failed: %s", e)
        raise RuntimeError(f"DeepInfra API request failed: {e}") from e
    try:
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error("Unexpected DeepInfra API response format: %s", e)
        raise RuntimeError("Malformed DeepInfra API response") from e


def entailment_check(evidence: str, claim: str) -> str:
    """
    Perform a simple entailment check on a claim against a piece of evidence.

    The model is instructed to answer strictly ``YES`` or ``NO``.  This helper
    utilises the chat API defined above.

    :param evidence: The evidence text to compare against.
    :param claim: The claim to be evaluated.
    :return: ``YES`` or ``NO`` depending on whether the claim is entailed.
    """
    system = {"role": "system", "content": "You are a careful scientific fact checker. Answer strictly YES or NO."}
    user = {
        "role": "user",
        "content": f"Evidence:\n\"\"\"\n{evidence}\n\"\"\"\nClaim:\n\"{claim}\"\nDoes the evidence fully entail the claim? Answer YES or NO only.",
    }
    out = chat([system, user], temperature=0.0, max_tokens=2)
    return out.strip().split()[0].upper()