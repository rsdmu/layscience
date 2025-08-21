import os, json, boto3
DDB = boto3.resource("dynamodb").Table(os.environ["DDB_TABLE"])
translate = boto3.client("translate")

def handler(event, context):
    job_id = event["pathParameters"]["id"]
    body = json.loads(event.get("body") or "{}")
    target = body.get("target_language","es")
    item = DDB.get_item(Key={"pk": f"job#{job_id}", "sk":"summary"}).get("Item")
    if not item: return resp(404, {"error":"not found"})
    p = item["payload"]
    res = translate.translate_text(Text=p["lay_summary"], SourceLanguageCode="en", TargetLanguageCode=target)
    p2 = dict(p)
    p2["lay_summary_translated"] = res["TranslatedText"]
    p2["language"] = target
    return resp(200, p2)

def resp(code, data):
    return {"statusCode": code, "headers": {"Access-Control-Allow-Origin": os.environ["ALLOW_ORIGIN"], "Content-Type":"application/json"}, "body": json.dumps(data)}
