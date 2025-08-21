import os, json, boto3
DDB = boto3.resource("dynamodb").Table(os.environ["DDB_TABLE"])

def handler(event, context):
    job_id = event["pathParameters"]["id"]
    item = DDB.get_item(Key={"pk": f"job#{job_id}", "sk":"summary"}).get("Item")
    if not item: return resp(404, {"error":"not found"})
    payload = item["payload"]
    payload["privacy"] = item.get("privacy","private")
    return resp(200, payload)

def resp(code, data):
    return {"statusCode": code, "headers": {"Access-Control-Allow-Origin": os.environ["ALLOW_ORIGIN"], "Content-Type":"application/json"}, "body": json.dumps(data)}
