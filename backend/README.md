
# LayScience Backend — Fixed

This backend provides a robust FastAPI service that accepts a DOI/URL **and/or** a PDF and returns a lay summary using **OpenAI GPT‑5** via the **Responses API**. It fixes:

- **State-of-the-art debugging** — every response includes an **`X-Request-ID`**; errors return structured JSON with `error`, `message`, `hint`, `where`, and `correlation_id`.

## Endpoints

  - Content types:
    - **JSON:** `{ "ref": "<doi or url>", "length": "default|extended" }`
    - **multipart/form-data:** fields `ref|doi|url` (optional), `pdf` (optional), `length` (`default`|`extended`)
  - Returns: `{ id, status, correlation_id }`

- `GET /api/v1/jobs/{id}` → `{ id, status, payload?, error? }`

- `GET /api/v1/summaries/{id}` → `{ id, status, payload? }` (payload contains the Markdown summary when `status=done`).

- `POST /api/v1/summaries/{id}/translate` → Translate the summary Markdown to a target language.

- `GET /healthz` → DB health & writability check.

## Environment variables

| Name | Default | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | *(required)* | Your OpenAI API key. |
| `OPENAI_MODEL` | `gpt-5` | Model to use. Pin to a dated snapshot in prod, e.g. `gpt-5-2025-08-07`. |
| `ALLOWED_ORIGINS` | `*` | CORS origins (comma-separated). |
| `UPLOADS_DIR` | `uploads` | Where uploaded PDFs are saved. |
| `DATA_DIR` | `data` | Base directory for app data. |
| `JOBS_DB_PATH` | `data/jobs.sqlite3` (auto-resolved) | SQLite DB file; falls back to `/tmp` if not writable. |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, etc. |
| `DRY_RUN` | `0` | If `1`, skip API calls and return mock output (useful for offline tests). |

## Quick local test

```bash
# 1) Create virtualenv
python -m venv .venv && source .venv/bin/activate

# 2) Install deps
pip install -r backend/requirements.txt

# 3) Export your API key
export OPENAI_API_KEY=sk-...

# 4) (Optional) Enable extra debug output
export LOG_LEVEL=DEBUG

# 5) Start the API
uvicorn backend.server.main:app --reload
```

### Smoke tests (cURL)

**JSON (DOI/URL only):**
```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/summaries   -H "content-type: application/json"   -d '{"ref":"https://arxiv.org/pdf/1706.03762.pdf","length":"default"}'
```

**Multipart (PDF + DOI/URL):**
```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/summaries   -F 'ref=10.1038/nrn3241'   -F 'length=extended'   -F 'pdf=@sample.pdf;type=application/pdf'
```

**Poll job:**
```bash
curl http://127.0.0.1:8000/api/v1/jobs/<JOB_ID>
curl http://127.0.0.1:8000/api/v1/summaries/<JOB_ID>
```

**DB health:**
```bash
curl http://127.0.0.1:8000/healthz
```

### Local API tests (pytest)

```bash
pip install pytest reportlab
pytest -q backend/tests/test_api.py
```

> Tip: set `DRY_RUN=1` to validate request/response flow without calling OpenAI.

## Docker

```bash
docker build -t layscience-backend ./
docker run --rm -p 8000:8000   -e OPENAI_API_KEY=$OPENAI_API_KEY   -e ALLOWED_ORIGINS=http://localhost:3000   -v $PWD/data:/app/data   -v $PWD/uploads:/app/uploads   layscience-backend
```

**Why this fixes “attempt to write a readonly database”:** the container writes to `/app/data/jobs.sqlite3`, which you bind-mount to `./data` on your host. If the mount is missing or read-only, the app automatically falls back to `/tmp` and `/healthz` will tell you. In serverless environments with read-only filesystems, set `JOBS_DB_PATH` to a networked DB (Postgres) or use a writable ephemeral path like `/tmp/jobs.sqlite3`.

## Deployment (Render / Railway / Fly.io)

1. **Create service** from this repo (Docker deploy recommended).
2. **Set environment variables**: `OPENAI_API_KEY`, `ALLOWED_ORIGINS`, `JOBS_DB_PATH=/tmp/jobs.sqlite3` (unless you attach a persistent disk), `LOG_LEVEL=INFO`.
3. **Persistent storage** (optional): attach a disk and set `JOBS_DB_PATH=/data/jobs.sqlite3` and `DATA_DIR=/data`.
4. **Health check**: target `/healthz` (expects HTTP 200).
5. **Pin model** in prod: set `OPENAI_MODEL=gpt-5-2025-08-07`.

## Notes on OpenAI API

This backend uses the **Responses API** with **GPT‑5** (`model: gpt-5`). See official docs:
- API quickstart and Responses API: https://platform.openai.com/docs/quickstart
- Responses API reference: https://platform.openai.com/docs/api-reference
- GPT‑5 model page (snapshots): https://platform.openai.com/docs/models/gpt-5

In your own code, prefer pinning to a dated snapshot for reproducibility.

## Troubleshooting

- **500 `attempt to write a readonly database`**: Your SQLite file or parent directory isn’t writable. Fix by setting `JOBS_DB_PATH` to a writable location or mount a disk. Check `/healthz` output.

- **CORS errors**: Set `ALLOWED_ORIGINS` to your frontend origin (comma-separated if multiple).
- **OpenAI auth**: Ensure `OPENAI_API_KEY` is set in the backend environment.
- **Long PDFs**: The server truncates extracted text to `MAX_SOURCE_CHARS` (default 120k). Override if needed.

---

© LayScience
