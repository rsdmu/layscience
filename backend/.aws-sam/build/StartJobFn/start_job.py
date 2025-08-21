import os, json, boto3, secrets
sf = boto3.client("stepfunctions")
DDB = boto3.resource("dynamodb").Table(os.environ["DDB_TABLE"])
SM_ARN = os.environ["STATE_MACHINE_ARN"]

def handler(event, context):
    body = json.loads(event.get("body") or "{}")
    privacy = body.get("privacy","ephemeral")
    job_id = "sum_" + secrets.token_hex(6)
    input_obj = {
        "job_id": job_id,
        "input": body.get("input"),
        "mode": body.get("mode","micro"),
        "privacy": "ephemeral" if privacy in ["process-only","ephemeral"] else privacy
    }
    exe = sf.start_execution(stateMachineArn=SM_ARN, input=json.dumps(input_obj))
    DDB.put_item(Item={"pk": f"job#{job_id}", "sk":"status", "status":"running"})
    return resp(202, {"id": job_id, "status": "running"})

def resp(code, data):
    return {"statusCode": code, "headers": {"Access-Control-Allow-Origin": os.environ["ALLOW_ORIGIN"], "Content-Type":"application/json"}, "body": json.dumps(data)}
