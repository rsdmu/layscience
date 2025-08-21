import os, json, boto3
DDB = boto3.resource("dynamodb").Table(os.environ["DDB_TABLE"])

def handler(event, context):
    job_id = (event.get("queryStringParameters") or {}).get("id")
    if not job_id: return resp(400, {"error":"id required"})
    item = DDB.get_item(Key={"pk": f"job#{job_id}", "sk":"status"}).get("Item")
    if not item:
        sum_item = DDB.get_item(Key={"pk": f"job#{job_id}", "sk":"summary"}).get("Item")
        if sum_item: return resp(200, {"id": job_id, "status": "done"})
        return resp(404, {"error":"not found"})
    return resp(200, {"id": job_id, "status": item["status"]})

def resp(code, data):
    return {"statusCode": code, "headers": {"Access-Control-Allow-Origin": os.environ["ALLOW_ORIGIN"], "Content-Type":"application/json"}, "body": json.dumps(data)}
