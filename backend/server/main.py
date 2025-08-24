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
import secrets
import smtplib
import hashlib
from email.message import EmailMessage
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from typing import Literal

from fastapi import FastAPI, HTTPException, UploadFile, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .services import jobs as jobs_store
from .services import (
    storage,
    summarizer,
    pdfio,
    fetcher,
    errors as err,
    arxiv,
    forum,
)

# ----------------------------------------------------------------------------
# Logging & error handling
# ----------------------------------------------------------------------------

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


class RequestIdFormatter(logging.Formatter):
    """Formatter that injects a default request_id if missing."""

    def format(self, record: logging.LogRecord) -> str:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return super().format(record)


_handler = logging.StreamHandler()
_handler.setFormatter(
    RequestIdFormatter(
        "%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s"
    )
)
logging.basicConfig(level=LOG_LEVEL, handlers=[_handler])
logger = logging.getLogger("layscience")

# FastAPI app
app = FastAPI(title="LayScience Summariser API", version="1.0.0")

# Persistent stores for demo account registration ---------------------------------


def _load_json(path: str) -> Dict[str, Any]:
    """Load a JSON file into a dictionary. Returns empty dict if missing."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            # Convert any ISO formatted datetimes back to datetime objects
            for rec in data.values():
                exp = rec.get("expires_at")
                if isinstance(exp, str):
                    try:
                        rec["expires_at"] = datetime.fromisoformat(exp)
                    except ValueError:
                        rec["expires_at"] = datetime.utcnow()
            return data
    except FileNotFoundError:
        return {}
    except Exception:  # pragma: no cover - log but continue
        logger.exception("Failed to load %s", path)
        return {}


def _save_json(path: str, payload: Dict[str, Any]) -> None:
    """Atomically write a dictionary to a JSON file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(
            payload,
            fh,
            default=lambda o: o.isoformat() if isinstance(o, datetime) else o,
        )
    os.replace(tmp, path)


DATA_DIR = os.getenv("DATA_DIR", "data")
ACCOUNTS_PATH = os.path.join(DATA_DIR, "accounts.json")
PENDING_PATH = os.path.join(DATA_DIR, "pending_codes.json")
FEEDBACK_PATH = os.path.join(DATA_DIR, "feedback.json")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")

# Load any existing account data from disk
accounts: Dict[str, Dict[str, Any]] = _load_json(ACCOUNTS_PATH)
pending_codes: Dict[str, Dict[str, Any]] = _load_json(PENDING_PATH)


def _send_verification_email(to: str, code: str) -> None:
    mail_api_key = os.getenv("MAIL_API_KEY")
    if mail_api_key:
        from_email = os.getenv("MAIL_FROM", "no-reply@mail.layscience.ai")
        app_name = os.getenv("APP_NAME", "LayScience")
        try:
            import resend

            resend.api_key = mail_api_key
            resend.Emails.send(
                {
                    "from": from_email,
                    "to": [to],
                    "subject": f"{app_name} verification code",
                    "text": f"Your verification code is {code}",
                }
            )
        except Exception:  # pragma: no cover - log but continue
            logger.exception("Failed to send verification email via Resend")
        return

    host = os.getenv("SMTP_HOST")
    # Default to the standard SMTP submission port if none provided
    port = int(os.getenv("SMTP_PORT") or 587)
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASS")

    app_name = os.getenv("APP_NAME", "LayScience")
    from_email = user or os.getenv("MAIL_FROM", "no-reply@mail.layscience.ai")
    msg = EmailMessage()
    msg["Subject"] = f"{app_name} verification code"
    msg["From"] = from_email
    msg["To"] = to
    msg.set_content(f"Your verification code is {code}")

    if host:
        with smtplib.SMTP(host, port) as server:
            server.ehlo()
            if os.getenv("SMTP_TLS") == "1":
                server.starttls()
                server.ehlo()
            if user and password:
                server.login(user, password)
            server.send_message(msg)
    else:  # pragma: no cover - fallback for dev environments
        logger.info(f"Verification code for {to}: {code}")


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
        return JSONResponse(
            status_code=e.status_code, content=payload, headers={"X-Request-ID": req_id}
        )
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
        return JSONResponse(
            status_code=500, content=payload, headers={"X-Request-ID": req_id}
        )
    duration_ms = int((time.time() - start) * 1000)
    response.headers["X-Request-ID"] = req_id
    response.headers["X-Response-Time-ms"] = str(duration_ms)
    return response


# Pydantic schema for JSON input
class StartJobJSON(BaseModel):
    ref: Optional[str] = Field(default=None, description="DOI or URL")
    length: Literal["default", "extended"] = "default"
    mode: Literal["default", "detailed", "funny"] = "default"
    language: Literal["en", "fa", "fr", "es", "de"] = "en"


def _normalize_ref(
    ref: Optional[str], doi: Optional[str], url: Optional[str]
) -> Optional[str]:
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


class RegisterRequest(BaseModel):
    username: str
    email: str


class VerifyRequest(BaseModel):
    email: str
    code: str


class ResendRequest(BaseModel):
    email: str


class DeleteAccountRequest(BaseModel):
    email: str


def _generate_code() -> str:
    """Generate a 6-digit verification code using a cryptographically strong RNG."""
    return f"{secrets.randbelow(1_000_000):06d}"


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


@app.post("/api/v1/register")
def register(req: RegisterRequest):
    code = _generate_code()
    pending_codes[req.email] = {
        "code": code,
        "code_hash": _hash_code(code),
        "username": req.username,
        "expires_at": datetime.utcnow() + timedelta(minutes=10),
        "attempts": 0,
        "resent": 0,
    }
    _save_json(PENDING_PATH, pending_codes)
    _send_verification_email(req.email, code)
    resp = {"status": "sent"}
    if not os.getenv("SMTP_HOST"):
        resp["dev_hint"] = "code logged to server"
    return resp


@app.post("/api/v1/resend")
def resend(req: ResendRequest):
    record = pending_codes.get(req.email)
    if record and datetime.utcnow() < record.get("expires_at", datetime.utcnow()):
        code = record["code"]
    else:
        code = _generate_code()
        pending_codes[req.email] = {
            "code": code,
            "code_hash": _hash_code(code),
            "username": record.get("username") if record else "",
            "expires_at": datetime.utcnow() + timedelta(minutes=10),
            "attempts": 0,
            "resent": 0,
        }
        record = pending_codes[req.email]
    record["resent"] = record.get("resent", 0) + 1
    _save_json(PENDING_PATH, pending_codes)
    _send_verification_email(req.email, code)
    resp = {"status": "resent"}
    if not os.getenv("SMTP_HOST"):
        resp["dev_hint"] = "code logged to server"
    return resp


@app.post("/api/v1/verify")
def verify(req: VerifyRequest):
    record = pending_codes.get(req.email)
    if not record or datetime.utcnow() > record.get("expires_at", datetime.utcnow()):
        raise HTTPException(status_code=400, detail="Invalid or expired code")
    if not secrets.compare_digest(record["code_hash"], _hash_code(req.code)):
        record["attempts"] = record.get("attempts", 0) + 1
        _save_json(PENDING_PATH, pending_codes)
        raise HTTPException(status_code=400, detail="Invalid code")
    accounts[req.email] = {"username": record.get("username")}
    pending_codes.pop(req.email, None)
    _save_json(ACCOUNTS_PATH, accounts)
    _save_json(PENDING_PATH, pending_codes)
    return {"status": "verified"}


@app.delete("/api/v1/account")
def delete_account(req: DeleteAccountRequest, request: Request):
    """Delete an existing account."""
    # Optional auth header for future use
    request.headers.get("Authorization")  # no-op
    if req.email not in accounts:
        raise HTTPException(status_code=404, detail="Account not found")
    accounts.pop(req.email, None)
    _save_json(ACCOUNTS_PATH, accounts)
    return {"status": "deleted"}


@app.get("/api/v1/admin/users")
def admin_users(request: Request):
    token = request.headers.get("X-Admin-Token")
    if not ADMIN_TOKEN or not secrets.compare_digest(token or "", ADMIN_TOKEN):
        raise HTTPException(status_code=401)
    return [
        {"email": email, "username": rec.get("username")}
        for email, rec in accounts.items()
    ]

# Feedback forum models ------------------------------------------------------

class FeedbackTopic(BaseModel):
    title: str = Field(..., max_length=100)
    body: str = Field(..., max_length=1000)
    email: Optional[str] = None

class FeedbackReply(BaseModel):
    body: str = Field(..., max_length=1000)
    email: Optional[str] = None

@app.get("/api/v1/feedback/topics")
def list_feedback_topics(page: int = 1):
    """Return paginated list of feedback topics."""
    return {"topics": forum.list_topics(page)}

@app.post("/api/v1/feedback/topics")
def create_feedback_topic(topic: FeedbackTopic):
    """Create a new feedback topic."""
    topic_id = forum.create_topic(topic.title, topic.body, topic.email)
    return {"id": topic_id, "title": topic.title, "body": topic.body, "email": topic.email}

@app.get("/api/v1/feedback/topics/{topic_id}/replies")
def list_feedback_replies(topic_id: int):
    """List replies for a given topic."""
    return {"replies": forum.list_replies(topic_id)}

@app.post("/api/v1/feedback/topics/{topic_id}/replies")
def create_feedback_reply(topic_id: int, reply: FeedbackReply):
    """Add a reply to a feedback topic."""
    reply_id = forum.create_reply(topic_id, reply.body, reply.email)
    return {"id": reply_id, "topic_id": topic_id, "body": reply.body, "email": reply.email}


class FeedbackSurvey(BaseModel):
    ease: int = Field(..., ge=1, le=5)
    clarity: int = Field(..., ge=1, le=5)
    improvement: str = Field(..., max_length=100)


@app.post("/api/v1/feedback/survey")
def feedback_survey(survey: FeedbackSurvey):
    """Persist a simple feedback survey submission."""
    entry = {
        "ease": survey.ease,
        "clarity": survey.clarity,
        "improvement": survey.improvement,
        "ts": datetime.utcnow().isoformat(),
    }
    try:
        with open(FEEDBACK_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        data = []
    data.append(entry)
    os.makedirs(os.path.dirname(FEEDBACK_PATH), exist_ok=True)
    with open(FEEDBACK_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    return {"status": "ok"}


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
):
    """
    Start a summarisation job.

    This endpoint accepts either JSON (application/json) with a ``ref`` and
    optional ``length`` field, or a multipart form with fields ``ref``/``doi``/``url``,
    optional ``pdf`` and ``length``.  The server stores the uploaded PDF,
    creates a job record and schedules processing in a background task.
    """
    rid = getattr(request.state, "request_id", "-")

    content_type = request.headers.get("content-type", "")
    ref = doi = url = None
    length = "default"
    mode = "default"
    language = "en"
    pdf: Optional[UploadFile] = None

    if content_type.startswith("application/json"):
        data = await request.json()
        body = StartJobJSON.model_validate(data)
        ref = body.ref
        length = body.length or length
        mode = body.mode or mode
        language = body.language or language
    else:
        form = await request.form()
        ref = form.get("ref")
        doi = form.get("doi")
        url = form.get("url")
        length = form.get("length", length)
        mode = form.get("mode", mode)
        language = form.get("language", language)
        pdf = form.get("pdf")  # may be UploadFile or None

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
    if mode not in ("default", "detailed", "funny"):
        raise err.BadRequest(
            "invalid_mode",
            "mode must be 'default', 'detailed' or 'funny'",
            where="start_summary",
        )
    if language not in ("en", "fa", "fr", "es", "de"):
        raise err.BadRequest(
            "invalid_language",
            "language must be one of 'en','fa','fr','es','de'",
            where="start_summary",
        )

    if mode == "detailed":
        length = "extended"

    saved_pdf_path: Optional[str] = None
    saved_pdf_name: Optional[str] = None
    if pdf is not None:
        if not hasattr(pdf, "filename"):
            raise err.BadRequest(
                "invalid_file",
                "Expected file upload for 'pdf'.",
                where="start_summary",
            )
        if not pdf.filename:
            raise err.BadRequest(
                "invalid_file",
                "Uploaded file has no filename.",
                where="start_summary",
            )
        if not pdf.content_type or "pdf" not in pdf.content_type.lower():
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
            "mode": mode,
            "language": language,
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
        mode = payload.get("mode", "default")
        language = payload.get("language", "en")
        if mode == "detailed":
            length = "extended"
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
        if mode == "detailed":
            sys_prompt += "\nWrite a detailed lay summary in five short paragraphs."
        elif mode == "funny":
            sys_prompt += "\nWrite the lay summary in a humorous and light-hearted tone while staying accurate."
        if language != "en":
            lang_name = {
                "fa": "Persian",
                "fr": "French",
                "es": "Spanish",
                "de": "German",
            }.get(language, "English")
            sys_prompt += f"\nRespond in {lang_name}."
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
        "error": (
            {
                "code": j.get("error_code"),
                "message": j.get("error_message"),
                "where": j.get("error_where"),
                "hint": j.get("error_hint"),
            }
            if j.get("error_code")
            else None
        ),
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


# ----------------------------------------------------------------------------
# arXiv helpers
# ----------------------------------------------------------------------------


@app.get("/api/v1/arxiv/search", tags=["arxiv"])
def arxiv_search(q: str, max_results: int = 50):
    """Search arXiv by title/keywords.

    Returns a JSON object with the original query, number of results and the
    normalised result list.
    """
    results = arxiv.search(q, max_results=max_results)
    return {"query": q, "count": len(results), "results": results}


@app.get("/api/v1/arxiv/pdf/{arxiv_id}", tags=["arxiv"])
def arxiv_pdf(arxiv_id: str):
    """Return the direct PDF URL for the given arXiv identifier."""
    return {"id": arxiv_id, "pdf_url": arxiv.pdf_url(arxiv_id)}
