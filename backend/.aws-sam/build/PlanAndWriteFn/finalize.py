import os, time, boto3

DDB = boto3.resource("dynamodb").Table(os.environ["DDB_TABLE"])

def handler(event, context):
    job_id = event["job_id"]
    draft = event["checked"]
    payload = {
        "mode": draft.get("mode"),
        "lay_summary": draft.get("lay_summary"),
        "headline": draft.get("headline"),
        "keywords": draft.get("keywords", []),
        "jargon_definitions": draft.get("jargon_definitions", {}),
        "sentences": draft.get("sentences", []),
        "reading_level": event.get("reading", {}),
        "disclaimers": event.get("disclaimers", []),
        "language": "en"
    }
    ttl = None
    if event.get("privacy") == "ephemeral":
        ttl = int(time.time()) + 3600
    item = {
        "pk": f"job#{job_id}",
        "sk": "summary",
        "status": "done",
        "payload": payload,
        "privacy": event.get("privacy","private")
    }
    if ttl is not None:
        item["ttl"] = ttl
    DDB.put_item(Item=item)
    # also mark status as done
    DDB.put_item(Item={"pk": f"job#{job_id}", "sk":"status", "status":"done"})
    return { "job_id": job_id, "status": "done" }
