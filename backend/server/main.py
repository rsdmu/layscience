"""
Main entry point for the LayScience summarisation API.

This FastAPI app exposes endpoints to start a summarisation job from a DOI/URL or PDF,
poll job status, and retrieve the finished summary.  Jobs are persisted in an
SQLite database and processed asynchronously via FastAPI background tasks.

Environment variables control model selection, API key, CORS origins and
paths for uploads and the job database.  See ``backend/README.md`` for details.
"""

import os
import uuid
import time
import json
import logging
import traceback
from typing import Optional, Dict, Any
from datetime import datetime
from typing import Literal

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

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


class RequestIdFilter(logging.Filter):
    """Ensure all log records have a request_id attribute."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


logger.addFilter(RequestIdFilter())

# FastAPI app
app = FastAPI(title="LayScience Summariser API", version="1.0.0")

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


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """
    Middleware that assigns a request ID to every incoming request and
    attaches it to logs and responses.  Handles user‑facing errors and
    unexpected exceptions uniformly.
    """
    req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = req_id
    start = time.time()
    try:
        response = await call_next(request)
    except err.UserFacingError as e:
        # user‑facing errors: return structured JSON
        logger.error(f"{e.code}: {e.public_message}", extra={"request_id": req_id})
        payload = {
            "error": e.code,
            "message": e.public_message,
            "hint": e.hint,
            "where": e.where,
            "correlation_id": req_id,
        }
        return JSONResponse(status_code=e.status_code, content=payload, headers={"X-Request-ID": req_id})
    except Exception as e:  # pragma: no cover
        # catch all unexpected exceptions
        tb = traceback.format_exc(limit=3)
        logger.exception("Unhandled error", extra={"request_id": req_id})
        payload = {
            "error": "internal_server_error",
            "message": "An unexpected error occurred.",
            "hint": "Check server logs with the given correlation id.",
            "where": "middleware",
            "correlation_id": req_id,
            "debug": tb if os.getenv("DEBUG") == "1" else None,
        }
        return JSONResponse(status_code=500, content=payload, headers={"X-Request-ID": req_id})
    duration_ms = int((time.time() - start) * 1000)
    response.headers["X-Request-ID"] = req_id
    response.headers["X-Response-Time-ms"] = str(duration_ms)
    return response


# Pydantic schema for JSON input
class StartJobJSON(BaseModel):
    ref: Optional[str] = Field(default=None, description="DOI or URL")
    length: Literal["default", "extended"] = "default"


def _normalize_ref(ref: Optional[str], doi: Optional[str], url: Optional[str]) -> Optional[str]:
    """Choose the first non‑empty reference value among ref, doi and url."""
    return ref or doi or url


@app.get("/healthz")
def healthz():
    """Simple health check that reports DB status and current UTC time."""
    status = jobs_store.health()
    return {
        "ok": status.get("ok", False),
        "db": status.get("db_path"),
        "time": datetime.utcnow().isoformat() + "Z",
    }


@app.get("/api/v1/version")
def version():
    """Return API name and version."""
    return {"name": "layscience-backend", "version": "1.0.0"}


@app.post(
    "/api/v1/summaries",
    tags=["summaries"],
)
@app.post("/api/v1/summary")
@app.post("/summaries")
@app.post("/summary")
async def start_summary(
    background: BackgroundTasks,
    request: Request,
    ref: Optional[str] = Form(default=None),
    doi: Optional[str] = Form(default=None),
    url: Optional[str] = Form(default=None),
    length: str = Form(default="default"),
    pdf: Optional[UploadFile] = File(default=None),
    body: Optional[StartJobJSON] = None,
):
    """
    Start a summarisation job.

    This endpoint accepts either JSON (application/json) with a ``ref`` and
    optional ``length`` field, or a multipart form with fields ``ref``/``doi``/``url``,
    optional ``pdf`` and ``length``.  The server stores the uploaded PDF,
    creates a job record and schedules processing in a background task.
    """
    rid = getattr(request.state, "request_id", "-")

    # If JSON body provided and no form fields, use body
    if body and not (ref or doi or url or pdf):
        ref = body.ref
        length = body.length or length

    # Validate at least one input
    ref_value = _normalize_ref(ref, doi, url)
    if not ref_value and not pdf:
        raise err.BadRequest(
            "missing_input",
            "Provide at least a DOI/URL or upload a PDF.",
            where="start_summary",
        )

    if length not in ("default", "extended"):
        raise err.BadRequest(
            "invalid_length",
            "length must be 'default' or 'extended'",
            where="start_summary",
        )

    # Save uploaded PDF if provided
    saved_pdf_path: Optional[str] = None
    saved_pdf_name: Optional[str] = None
    if pdf is not None:
        if not pdf.filename:
            raise err.BadRequest(
                "invalid_file",
                "Uploaded file has no filename.",
                where="start_summary",
            )
        if not pdf.content_type or "pdf" not in pdf.content_type.lower():
            # allow unknown type but enforce .pdf extension if present
            if not str(pdf.filename).lower().endswith(".pdf"):
                raise err.BadRequest(
                    "invalid_file_type",
                    "Only PDF files are supported for the 'pdf' field.",
                    where="start_summary",
                )
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
        },
    )

    # Launch background processing
    background.add_task(process_job, job_id, request_id=rid)
    return {"id": job_id, "status": "queued", "correlation_id": rid}


async def process_job(job_id: str, request_id: str):
    """
    Background worker that processes a summarisation job.  It extracts the text
    from the uploaded PDF or fetches the content from a DOI/URL, calls the
    summariser and writes the result or error back to the job record.
    """
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
            text, meta = fetcher.fetch_and_extract(ref)
        else:
            raise err.BadRequest(
                "missing_input",
                "No input provided.",
                where="process_job",
            )

        if not text.strip():
            raise err.UserFacingError(
                code="empty_content",
                public_message="Couldn't extract any text. If the paper is paywalled or scanned, please upload a direct PDF or paste the abstract.",
                where="process_job",
                status_code=422,
                hint="Try uploading the PDF or provide a different URL/DOI.",
            )

        # Summarise using OpenAI
        sys_prompt = summarizer.LAY_SUMMARY_SYSTEM_PROMPT
        summary_md = summarizer.summarise(
            text=text,
            meta=meta,
            length=length,
            system_prompt=sys_prompt,
        )

        result = {
            "meta": meta,
            "length": length,
            "summary": summary_md,
            "model": summarizer.MODEL_NAME,
            "finished_at": datetime.utcnow().isoformat() + "Z",
        }
        jobs_store.update(job_id, status="done", result=result)
        logger.info(f"Job {job_id} done", extra={"request_id": request_id})
    except err.UserFacingError as e:
        jobs_store.update(
            job_id,
            status="failed",
            error_code=e.code,
            error_message=e.public_message,
            error_where=e.where,
            error_hint=e.hint,
        )
        logger.error(
            f"User‑facing error for job {job_id}: {e.code}",
            extra={"request_id": request_id},
        )
    except Exception as e:
        tb = traceback.format_exc(limit=3)
        jobs_store.update(
            job_id,
            status="failed",
            error_code="internal",
            error_message=str(e),
            error_where="process_job",
            error_hint=tb,
        )
        logger.exception(f"Job {job_id} crashed", extra={"request_id": request_id})


@app.get("/api/v1/jobs/{job_id}")
@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    """Return the job record with status, payload and error details."""
    j = jobs_store.get(job_id)
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "id": job_id,
        "status": j["status"],
        "payload": j.get("payload"),
        "error": {
            "code": j.get("error_code"),
            "message": j.get("error_message"),
            "where": j.get("error_where"),
            "hint": j.get("error_hint"),
        }
        if j.get("error_code")
        else None,
    }


@app.get("/api/v1/summaries/{job_id}")
@app.get("/api/v1/summary/{job_id}")
@app.get("/summaries/{job_id}")
@app.get("/summary/{job_id}")
def get_summary(job_id: str):
    """
    Return the finished summary for a completed job, or the current status if not done.
    """
    j = jobs_store.get(job_id)
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    if j["status"] != "done":
        return {"id": job_id, "status": j["status"], "error": j.get("error")}
    return {"id": job_id, "status": "done", "payload": j["result"]}