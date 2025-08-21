import os
from ..common.parsing import fetch_pdf_to_s3, parse_pdf_from_s3

BUCKET = os.environ["UPLOAD_BUCKET"]

def handler(event, context):
    job_id = event["job_id"]
    s3_key = f"uploads/{job_id}.pdf"
    key = fetch_pdf_to_s3(event["input"], BUCKET, s3_key)
    text = parse_pdf_from_s3(BUCKET, key)
    return { **event, "s3_key": key, "text": text }
