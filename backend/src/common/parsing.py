import io, os
import boto3, requests
from pdfminer.high_level import extract_text
from .util import is_probably_scanned

s3 = boto3.client("s3")
textract = boto3.client("textract")

def fetch_pdf_to_s3(src: dict, bucket: str, key: str):
    if "s3_key" in src:
        return src["s3_key"]
    if "doi" in src:
        url = f"https://doi.org/{src['doi']}"
        r = requests.get(url, allow_redirects=True, timeout=30)
        r.raise_for_status()
        content = r.content
    elif "url" in src:
        r = requests.get(src["url"], timeout=30)
        r.raise_for_status()
        content = r.content
    else:
        raise ValueError("No valid source provided")
    s3.put_object(Bucket=bucket, Key=key, Body=content, ContentType="application/pdf")
    return key

def parse_pdf_from_s3(bucket: str, key: str) -> str:
    obj = s3.get_object(Bucket=bucket, Key=key)
    b = obj["Body"].read()
    text = extract_text(io.BytesIO(b)) or ""
    if len(text.strip()) < 500 and is_probably_scanned(b):
        resp = textract.detect_document_text(Document={'Bytes': b})
        lines = [item["DetectedText"] for item in resp["Blocks"] if item["BlockType"]=="LINE"]
        text = "\n".join(lines)
    return text
