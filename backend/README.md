# LayScience Backend (FastAPI)

This backend exposes a small set of endpoints to upload a PDF, start a summarisation job, check its status, fetch the finished summary, and translate the summary.

It is designed to **avoid the `Failed to fetch` problem** by:
- Returning **proper CORS headers** (configurable via `ALLOWED_ORIGINS`).
- Using clear JSON response codes and messages.
- Providing a **local development proxy** on the frontend so that you can also bypass CORS during dev.

## Endpoints

- `GET /api/v1/health` – quick health check.
- `POST /api/v1/upload` – multipart upload of a PDF. Returns `{file_id}`.
- `POST /api/v1/jobs` – start a job:

```json
{
  "input": { "doi": "10.1038/...", "url": "https://...", "file_id": "..." },
  "mode": "micro",
  "privacy": "private"
}
```

- `GET /api/v1/jobs/{id}` – returns `{id, status}` where status is one of `running|done|failed`.
- `GET /api/v1/summaries/{id}` – returns the finished summary.
- `POST /api/v1/summaries/{id}/translate` – `{ target_language: "fr" }`, returns translated summary.

## Configuration

Create a `.env` file based on `.env.example`:

```ini
ALLOWED_ORIGINS=http://localhost:3000
OPENAI_API_KEY=sk-...
# Set this during development if you do not want to call the LLM:
# MOCK_SUMMARIZER=1
```

## Run locally

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn server.main:app --reload --port 8000
```

The interactive docs will be available at `http://localhost:8000/docs`.

## Docker

```bash
docker build -t layscience-backend .
docker run --rm -p 8000:8000 -e ALLOWED_ORIGINS=http://localhost:3000 -e OPENAI_API_KEY=$OPENAI_API_KEY layscience-backend
```

## Notes

- Uploaded files are saved under `uploads/` locally. Clean them up periodically.
- Jobs and results are stored in a lightweight SQLite file `jobs.sqlite3`.
- The server runs background tasks within the same process – simple and robust for small-to-medium loads.
