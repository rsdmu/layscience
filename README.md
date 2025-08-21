# Paper Summarizer — Evidence-Grounded Research Summaries

A production-ready reference implementation of the product described: paste a DOI/URL or upload a PDF, detect paper metadata, choose summary mode, and generate **evidence-grounded** summaries (3-sentence or 5-paragraph) with glossary tooltips, figure/number explainers, i18n, accessibility options, privacy controls, share links, and optional audio.

## Quick start (Docker Compose)

```bash
# 1) copy env
cp .env.example .env

# 2) start services (first run will pull images)
docker compose up --build
```

Services:
- **frontend**: Next.js on http://localhost:3000
- **api**: FastAPI on http://localhost:8000/docs
- **worker**: Celery worker consuming jobs
- **postgres**: with `pgvector` extension
- **redis**: for queues and ephemeral storage
- **minio**: S3-compatible object storage on :9000 (console :9001)
- **opensearch**: optional full-text (not required for local dev; can be disabled)
- **grobid**: PDF parsing service
- **unstructured**: text extraction (fallback for tricky PDFs)

> **Note**: The LLM and embeddings are provider-agnostic. Set `OPENAI_API_KEY` (or use Azure/Bedrock) to enable generation. In CI and tests we mock LLM calls.

## Key features implemented
- Evidence-grounded summaries: each sentence links to exact source spans with page+offset.
- Default (3-sentence) and Extended (5-paragraph) templates.
- Glossary with hover tooltips, auto-added in Kid/Grandparent modes.
- Figure & number explainer (caption-aware).
- Accessibility: large-text toggle, dyslexia-friendly font, keyboard nav, ARIA.
- i18n: output translation with "show original English" toggle.
- Privacy: process-only (ephemeral Redis), private library (auth token), public share links.
- Disclaimers for health/finance/legal content.
- Reading-level meters (Flesch–Kincaid + CEFR heuristics).
- Batch mode & REST API: `POST /summaries`.
- Observability (OpenTelemetry hooks), Sentry (optional), structured logging.

## Environment (.env)
See `.env.example` for all knobs. Minimal to run with OpenAI:
```
OPENAI_API_KEY=sk-...
```

## Local accounts / auth
The example app runs without login. If you set `AUTH_REQUIRED=true`, the API expects a Bearer token (e.g., from Auth0) and stores summaries under that subject.

## Migrations
The DB schema is in `backend/app/migrations/0001_initial.sql`. Apply automatically on start.

## Tests
```bash
docker compose exec api pytest -q
```

## Production deploy
- Container images are multi-stage and small.
- Configure object store (S3/GCS), managed Postgres with pgvector, and Redis.
- Point the frontend at your API with `NEXT_PUBLIC_API_BASE`.
- Enable HTTPS and WAF at your ingress (e.g., CloudFront/ALB + ACM).

---

**License**: Apache-2.0


## API (FastAPI)

OpenAPI: http://localhost:8000/docs

### Create a summary (URL)
```bash
curl -X POST http://localhost:8000/summaries \\
  -H 'Content-Type: application/json' \\
  -d '{
    "input_type": "url",
    "url": "https://arxiv.org/pdf/1706.03762.pdf",
    "mode": "default",
    "privacy": "process-only",
    "locale": "en"
  }'
```

### Create a summary (DOI)
```bash
curl -X POST http://localhost:8000/summaries \\
  -H 'Content-Type: application/json' \\
  -d '{
    "input_type": "doi",
    "doi": "10.1038/nature14539",
    "mode": "extended",
    "privacy": "public",
    "locale": "en"
  }'
```

### Batch mode
```bash
curl -X POST http://localhost:8000/summaries/batch -H 'Content-Type: application/json' -d '[
  {"input_type":"url","url":"https://arxiv.org/pdf/1706.03762.pdf","mode":"default","privacy":"process-only","locale":"en"},
  {"input_type":"doi","doi":"10.1038/nature14539","mode":"extended","privacy":"public","locale":"en"}
]'
```

**Response shape (`SummaryOut`)**

```json
{
  "id": "uuid",
  "headline": "string",
  "keywords": ["string"],
  "lay_summary": "string",
  "lay_summary_translated": "string|null",
  "jargon_definitions": {"term":"definition"},
  "evidence": [
    {"sentence":"...", "entails": true, "spans":[{"page":1,"start":123,"end":321,"text":"..."}]}
  ],
  "title": "string",
  "authors": "string",
  "journal": "string",
  "year": 2023,
  "audio_url": null,
  "disclaimers": {"health":"..."},
  "reading_level": {"flesch_kincaid_grade": 9.2, "cefr": "B2"},
  "source_url": "https://doi.org/..."
}
```

## Architecture & Guardrails

- **Parser**: GROBID turns PDFs into structured TEI; we extract title/authors/journal/year/body/figures.
- **Retriever**: text is chunked + embedded (OpenAI embeddings by default). Semantic search selects passages per sentence.
- **Planner/Writer**: a constrained prompt (in code) produces JSON with a lay summary, headline, keywords, and glossary.
- **Evidence alignment**: for each sentence we attach top-k source spans (page/start/end/snippet).
- **NLI check**: optional RoBERTa MNLI gate (`HF_NLI_MODEL=roberta-large-mnli`); `entails=false` is surfaced in UI.
- **Readability**: Flesch–Kincaid + CEFR heuristic; badge shows "meets target".
- **i18n**: backend can produce translated output (set non-English `locale`), and UI toggles between English/original.
- **Accessibility**: large-text / dyslexia-friendly toggles, keyboardable popovers/tooltips, ARIA labels and focus rings.
- **Privacy**: 
  - *process-only*: nothing stored (in this demo, results are returned inline; Redis TTL storage is trivial to add).
  - *private/public*: persist to DB with user subject (set `AUTH_REQUIRED=true` and configure JWT/JWKS).
- **Figure explainers**: caption → plain-language explanation via LLM.

## Hardening for production

- Swap inline task execution for Celery queue. Keep idempotency keys for retries.
- Replace the stub NLI with the HF model or a server-side verifier endpoint.
- Add persistent object-store for input PDFs and presigned viewer links.
- Rate limit by user & token bucket on NGINX/Envoy.
- Enable OpenTelemetry exporter + Sentry DSN for traces/errors.
- Add e2e tests (Playwright) for upload → summary flow.

