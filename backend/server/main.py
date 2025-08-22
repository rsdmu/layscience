import os
import uuid
import time
import json
import logging
import traceback
from typing import Optional, Dict, Any, Union
from datetime import datetime
from typing import Literal

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator

from .services import jobs as jobs_store
from .services import storage, summarizer, pdfio, fetcher, errors as err

# ----------------------------------------------------------------------------
# Logging & error handling
# ----------------------------------------------------------------------------

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s",
)
logger = logging.getLogger("layscience")

# Ensure record has request_id
class RequestIdFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True

logger.addFilter(RequestIdFilter())

app = FastAPI(title="LayScience Summarizer API", version="1.1.0")

# CORS -----------------------------------------------------------------------
ALLOWED = os.getenv("ALLOWED_ORIGINS", "*")
if ALLOWED == "*":
    origins = ["*"]
else:
    origins = [s.strip() for s in ALLOWED.split(",") if s.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

# Middleware to add request id and structured error handling -----------------
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = req_id
    start = time.time()
    try:
        response = await call_next(request)
    except err.UserFacingError as e:
        logger.error(f"{e.code}: {e.public_message}", extra={"request_id": req_id})
        payload = {
            "error": e.code,
            "message": e.public_message,
            "hint": e.hint,
            "where": e.where,
            "correlation_id": req_id,
        }
        return JSONResponse(status_code=e.status_code, content=payload, headers={"X-Request-ID": req_id})
    except Exception as e:  # pragma: no cover - catch-all
        tb = traceback.format_exc(limit=3)
        logger.exception("Unhandled error", extra={"request_id": req_id})
        payload = {
            "error": "internal_server_error",
            "message": "An unexpected error occurred.",
            "hint": "Check server logs with the given correlation id.",
            "where": "middleware",
            "correlation_id": req_id,
            "debug": tb if os.getenv("DEBUG") == "1" else None
        }
        return JSONResponse(status_code=500, content=payload, headers={"X-Request-ID": req_id})
    dur_ms = int((time.time() - start) * 1000)
    response.headers["X-Request-ID"] = req_id
    response.headers["X-Response-Time-ms"] = str(dur_ms)
    return response

# Error handlers for Pydantic / FastAPI HTTPException ------------------------
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, e: HTTPException):
    rid = getattr(request.state, "request_id", "-")
    logger.error(f"HTTPException {e.status_code}: {e.detail}", extra={"request_id": rid})
    content = {"error": "http_error", "message": str(e.detail), "correlation_id": rid}
    return JSONResponse(status_code=e.status_code, content=content, headers={"X-Request-ID": rid})

# Schemas --------------------------------------------------------------------
class StartJobJSON(BaseModel):
    ref: Optional[str] = Field(default=None, description="DOI or URL")
    length: Literal["default", "extended"] = "default"

# Union body: JSON or Multipart ----------------------------------------------
def _normalize_ref(ref: Optional[str], doi: Optional[str], url: Optional[str]) -> Optional[str]:
    # Prefer ref; else DOI; else URL
    return ref or doi or url

# Health endpoints ------------------------------------------------------------
@app.get("/healthz")
def healthz():
    status = jobs_store.health()
    return {"ok": status.get("ok", False), "db": status.get("db_path"), "time": datetime.utcnow().isoformat() + "Z"}

@app.get("/api/v1/version")
def version():
    return {"name": "layscience-backend", "version": "1.1.0"}

# Backwards-compat aliases to avoid 404s ------------------------------------
# Support both plural and singular forms
@app.post("/api/v1/summarize")
@app.post("/api/v1/summarise")  # UK spelling
@app.post("/api/v1/summaries")
@app.post("/api/v1/summary")
# Root-level aliases for older frontends
@app.post("/summarize")
@app.post("/summarise")
@app.post("/summaries")
@app.post("/summary")
async def start_summary(
    background: BackgroundTasks,
    request: Request,
    ref: Optional[str] = Form(default=None),
    doi: Optional[str] = Form(default=None),
    url: Optional[str] = Form(default=None),
    length: Optional[str] = Form(default="default"),
    pdf: Optional[UploadFile] = File(default=None),
    body: Optional[StartJobJSON] = None,
):
    """
    Start a summarization job.
    Accepts either JSON body or multipart form:
    - JSON: { "ref": "<doi or url>", "length": "default|extended" }
    - Multipart: fields ref|doi|url, optional 'pdf' file, and 'length'.
    """
    rid = getattr(request.state, "request_id", "-")

    # Accept JSON or multipart; FastAPI sends both depending on content-type.
    if body and not (ref or doi or url or pdf):
        ref = body.ref
        length = body.length or length

    # Validate inputs
    ref_value = _normalize_ref(ref, doi, url)
    if not ref_value and not pdf:
        raise err.BadRequest("missing_input", "Provide at least a DOI/URL or upload a PDF.", where="start_summary")

    if length not in ("default", "extended"):
        raise err.BadRequest("invalid_length", "length must be 'default' or 'extended'", where="start_summary")

    # Store uploaded PDF if provided
    saved_pdf_path = None
    saved_pdf_name = None
    if pdf is not None:
        if not pdf.filename:
            raise err.BadRequest("invalid_file", "Uploaded file has no filename.", where="start_summary")
        if not pdf.content_type or "pdf" not in pdf.content_type.lower():
            # allow unknown type but enforce .pdf extension if present
            if not str(pdf.filename).lower().endswith(".pdf"):
                raise err.BadRequest("invalid_file_type", "Only PDF files are supported for the 'pdf' field.", where="start_summary")
        saved_pdf_name, saved_pdf_path = storage.save_upload(pdf)

    # Create job record
    job_id = str(uuid.uuid4())
    jobs_store.create(
        job_id=job_id,
        status="queued",
        payload={
            "ref": ref_value,
            "length": length,
            "pdf_path": saved_pdf_path,
            "pdf_name": saved_pdf_name,
        }
    )

    # Launch background processing
    background.add_task(process_job, job_id, request_id=rid)
    return {"id": job_id, "status": "queued", "correlation_id": rid}

async def process_job(job_id: str, request_id: str):
    logger.info(f"Processing job {job_id}", extra={"request_id": request_id})
    job = jobs_store.get(job_id)
    if not job:
        logger.error("Job disappeared", extra={"request_id": request_id})
        return

    jobs_store.update(job_id, status="running")
    try:
        payload = job["payload"]
        length = payload.get("length", "default")
        ref = payload.get("ref")
        pdf_path = payload.get("pdf_path")

        # Acquire and parse content
        meta: Dict[str, Any] = {}
        text: str = ""

        if pdf_path:
            text, meta = pdfio.extract_text_and_meta(pdf_path)
            meta.setdefault("source", "uploaded_pdf")
        elif ref:
            # attempt to fetch
            text, meta = fetcher.fetch_and_extract(ref)
        else:
            raise err.BadRequest("missing_input", "No input provided.", where="process_job")

        if not text.strip():
            raise err.UserFacingError(
                code="empty_content",
                public_message="Couldn't extract any text. If the paper is paywalled or scanned, please upload a direct PDF or paste the abstract.",
                where="process_job",
                status_code=422,
                hint="Try uploading the PDF or provide a different URL/DOI."
            )

        # Summarize
        sys_prompt = summarizer.LAY_SUMMARY_SYSTEM_PROMPT
        summary_md = summarizer.summarize(text=text, meta=meta, length=length, system_prompt=sys_prompt)

        result = {
            "meta": meta,
            "length": length,
            "summary": summary_md,
            "model": summarizer.MODEL_NAME,
            "finished_at": datetime.utcnow().isoformat() + "Z"
        }
        jobs_store.update(job_id, status="done", result=result)
        logger.info(f"Job {job_id} done", extra={"request_id": request_id})
    except err.UserFacingError as e:
        jobs_store.update(job_id, status="failed", error={"code": e.code, "message": e.public_message, "hint": e.hint, "where": e.where})
        logger.error(f"User-facing error for job {job_id}: {e.code}", extra={"request_id": request_id})
    except Exception as e:
        tb = traceback.format_exc(limit=3)
        jobs_store.update(job_id, status="failed", error={"code": "internal", "message": str(e), "trace": tb})
        logger.exception(f"Job {job_id} crashed", extra={"request_id": request_id})

# Job polling endpoints ------------------------------------------------------
@app.get("/api/v1/jobs/{job_id}")
@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    j = jobs_store.get(job_id)
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"id": job_id, "status": j["status"], "payload": j.get("payload"), "error": j.get("error")}

@app.get("/api/v1/summaries/{job_id}")
@app.get("/api/v1/summary/{job_id}")
@app.get("/summaries/{job_id}")
@app.get("/summary/{job_id}")
def get_summary(job_id: str):
    j = jobs_store.get(job_id)
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    if j["status"] != "done":
        return {"id": job_id, "status": j["status"], "error": j.get("error")}
    return {"id": job_id, "status": "done", "payload": j["result"]}