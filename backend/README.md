# LayScience Backend

This folder implements a standalone FastAPI service for generating lay summaries of scientific papers.  The service accepts a DOI or URL pointing to a paper, or a direct PDF upload, extracts the paper’s text and metadata, and then sends a summarisation request to the OpenAI **Responses API** with GPT‑5.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/summaries` | Start a new summarisation job. Accepts either JSON (`{"ref": "<doi|url>", "length": "default|extended"}`) or multipart/form‑data with fields `ref|doi|url`, optional `pdf` file and `length`. Returns a job ID and status. |
| `GET` | `/api/v1/jobs/{id}` | Poll the status of a job. Returns the payload and any error details. |
| `GET` | `/api/v1/summaries/{id}` | Retrieve the summary Markdown once the job status is `done`. |
| `GET` | `/healthz` | Check DB health and service liveness. |

## Configuration

The backend uses environment variables for configuration:

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | *required* | Your OpenAI API key. |
| `OPENAI_MODEL` | `gpt-5` | The model name or snapshot (e.g. `gpt-5-2025-08-07`). |
| `ALLOWED_ORIGINS` | `*` | Comma‑separated list of CORS origins. |
| `UPLOADS_DIR` | `uploads` | Directory where uploaded PDFs are stored. |
| `DATA_DIR` | `data` | Base directory for data (used for the job DB). |
| `JOBS_DB_PATH` | `data/jobs.sqlite3` | SQLite database path; falls back to `/tmp/jobs.sqlite3` if unwritable. |
| `LOG_LEVEL` | `INFO` | Logging level. |
| `DRY_RUN` | `0` | Set to `1` to skip OpenAI API calls and return mock summaries. |

## Quick start

```bash
# create a virtual environment
python -m venv .venv && source .venv/bin/activate

# install dependencies
pip install -r backend/requirements.txt

# set your OpenAI key
export OPENAI_API_KEY=sk-...

# launch the API
uvicorn backend.server.main:app --reload
```

### Testing the API

Send a DOI/URL:

```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/summaries \
  -H "Content-Type: application/json" \
  -d '{"ref": "https://arxiv.org/pdf/1706.03762.pdf", "length": "default"}'
```

Upload a PDF:

```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/summaries \
  -F 'ref=10.1038/nrn3241' \
  -F 'length=extended' \
  -F 'pdf=@sample.pdf;type=application/pdf'
```

Poll job status:

```bash
curl http://127.0.0.1:8000/api/v1/jobs/<job_id>
```

Retrieve the finished summary:

```bash
curl http://127.0.0.1:8000/api/v1/summaries/<job_id>
```

## Deployment notes

In serverless environments (e.g. Vercel) the filesystem may be read‑only.  Set `JOBS_DB_PATH` to `/tmp/jobs.sqlite3` and `UPLOADS_DIR` to `/tmp/uploads` so that the service can write temporary files.  For persistent storage, consider deploying the backend on a platform that supports disks (e.g. Render, Railway or Fly.io) or connecting to an external database.

Ensure `OPENAI_API_KEY` and `OPENAI_MODEL` are set in your deployment environment.  To keep results consistent across future GPT‑5 snapshots, pin the model to a dated snapshot.