import os, json, boto3, uuid
S3 = boto3.client("s3")
BUCKET = os.environ["UPLOAD_BUCKET"]
ALLOWED = {"application/pdf"}

def handler(event, context):
    body = json.loads(event.get("body") or "{}")
    content_type = body.get("content_type","application/pdf")
    if content_type not in ALLOWED:
        return resp(400, {"error":"Only PDF allowed"})
    key = f"uploads/{uuid.uuid4().hex}.pdf"
    url = S3.generate_presigned_url("put_object", Params={"Bucket": BUCKET, "Key": key, "ContentType": content_type}, ExpiresIn=3600)
    return resp(200, {"key": key, "url": url})

def resp(code, data):
    return {"statusCode": code, "headers": cors(), "body": json.dumps(data)}

def cors():
    return {"Access-Control-Allow-Origin": os.environ["ALLOW_ORIGIN"], "Access-Control-Allow-Credentials":"true", "Content-Type":"application/json"}
