from ..common.util import new_id

def handler(event, context):
    body = event if isinstance(event, dict) else {}
    job_id = body.get("job_id") or new_id("sum")
    return {
        "job_id": job_id,
        "input": body["input"],
        "mode": body.get("mode","micro"),
        "privacy": "ephemeral" if body.get("privacy") in ["process-only","ephemeral"] else body.get("privacy","private")
    }
