
import os
import uuid
import shutil
import logging
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from .services import jobs, storage, summarizer, translator, pdfio

# --- logging ----------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("layscience")

# --- FastAPI app ------------------------------------------------------------
app = FastAPI(
    title="LayScience API",
    version="2.0.0",
    description="A compact, production-grade API for PDF summarisation and translation."
)

# CORS
_ALLOWED = os.getenv("ALLOWED_ORIGINS", "*")
if _ALLOWED == "*":
    allow_origins = ["*"]
else:
    allow_origins = [o.strip() for o in _ALLOWED.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# ensure local uploads directory exists (used when S3 not configured)
os.makedirs(storage.LOCAL_UPLOAD_DIR, exist_ok=True)

# --- Pydantic models --------------------------------------------------------
class Input(BaseModel):
    doi: Optional[str] = Field(default=None, description="DOI like 10.1038/s41586-020-2649-2")
    url: Optional[str] = Field(default=None, description="Direct URL to a PDF or page containing PDF")
    file_id: Optional[str] = Field(default=None, description="Internal uploaded file identifier")

class StartRequest(BaseModel):
    input: Input
    mode: str = Field(default="micro", description="micro|extended")
    privacy: str = Field(default="private", description="process-only|private|public")

class StartResponse(BaseModel):
    id: str
    status: str

class StatusResponse(BaseModel):
    id: str
    status: str

class SummaryResponse(BaseModel):
    id: str
    mode: str
    source: Dict[str, Any]
    summary: Dict[str, Any]
    privacy: str = "private"
    reading_time_min: Optional[int] = None
    disclaimers: Optional[str] = None

class TranslateRequest(BaseModel):
    target_language: str

# --- Routes -----------------------------------------------------------------
@app.get("/api/v1/health")
def health():
    return {"ok": True}

@app.post("/api/v1/upload", summary="Upload a PDF directly to the server")
async def upload(file: UploadFile = File(...)):
    if file.content_type not in ("application/pdf", "application/x-pdf"):
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported")
    file_id = str(uuid.uuid4())
    dest_path = storage.local_path_for(file_id)
    with open(dest_path, "wb") as out:
        shutil.copyfileobj(file.file, out)
    logger.info("Uploaded file saved: %s", dest_path)
    return {"file_id": file_id, "content_type": file.content_type}

@app.post("/api/v1/jobs", response_model=StartResponse, summary="Start summarisation job")
async def start_job(req: StartRequest, tasks: BackgroundTasks):
    try:
        job_id = jobs.create(req.dict())
    except Exception as e:
        logger.exception("Failed to create job")
        raise HTTPException(status_code=500, detail=str(e))

    tasks.add_task(_run_job, job_id)  # process in background
    return {"id": job_id, "status": "running"}

async def _run_job(job_id: str):
    try:
        data = jobs.get(job_id)
        inp = data["input"]

        # Determine source PDF
        source_info: Dict[str, Any] = {}
        if inp.get("file_id"):
            path = storage.local_path_for(inp["file_id"])
            if not os.path.exists(path):
                raise FileNotFoundError("Uploaded file not found")
            source_info = {"type": "upload", "file_id": inp["file_id"]}
        elif inp.get("url"):
            path = pdfio.fetch_pdf_from_url(inp["url"])
            source_info = {"type": "url", "url": inp["url"]}
        elif inp.get("doi"):
            url = pdfio.resolve_doi_to_pdf_url(inp["doi"])
            path = pdfio.fetch_pdf_from_url(url)
            source_info = {"type": "doi", "doi": inp["doi"], "resolved_url": url}
        else:
            raise ValueError("No valid input provided. Supply one of: doi, url, file_id")

        # Extract text
        text = pdfio.extract_text(path)
        if len(text.strip()) < 50:
            raise ValueError("Unable to extract sufficient text from the PDF")

        # Summarise
        mode = data.get("mode", "micro")
        summary = summarizer.summarise(text, mode=mode)

        # Assemble response
        payload = {
            "id": job_id,
            "mode": mode,
            "source": source_info,
            "summary": summary,
            "privacy": data.get("privacy", "private"),
            "reading_time_min": max(1, len(text.split()) // 200),
            "disclaimers": "LLM-generated summary. Verify critical claims with the original source."
        }
        jobs.finish(job_id, payload)
        logger.info("Job %s finished", job_id)
    except Exception as e:
        logger.exception("Job %s failed", job_id)
        jobs.fail(job_id, str(e))

@app.get("/api/v1/jobs/{job_id}", response_model=StatusResponse, summary="Get job status")
def get_status(job_id: str):
    j = jobs.get(job_id)
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"id": job_id, "status": j["status"]}

@app.get("/api/v1/summaries/{job_id}", response_model=SummaryResponse, summary="Fetch completed summary")
def get_summary(job_id: str):
    j = jobs.get(job_id)
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    if j["status"] != "done":
        raise HTTPException(status_code=409, detail="Job not finished yet")
    return j["payload"]

@app.post("/api/v1/summaries/{job_id}/translate")
def translate(job_id: str, req: TranslateRequest):
    j = jobs.get(job_id)
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    if j["status"] != "done":
        raise HTTPException(status_code=409, detail="Job not finished yet")
    target = req.target_language
    try:
        translated = translator.translate_summary(j["payload"]["summary"], target_language=target)
    except Exception as e:
        logger.exception("Translation failed")
        raise HTTPException(status_code=500, detail=str(e))
    return {"id": job_id, "target_language": target, "summary": translated}
