# Paper Summarizer — Evidence-Grounded Research Summaries

A serverless application that turns research papers into short or extended lay summaries with links back to supporting evidence.

## Repository layout

- `backend/` – AWS SAM application (Lambdas, Step Functions, S3 and DynamoDB resources).
- `frontend/` – Next.js interface.

## Quick start

### Backend (Python + AWS SAM)

Prerequisites: Python 3.11, AWS credentials and the [SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html).

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
sam build
sam local start-api -p 8000  # or: sam deploy --guided
```

The summarization step calls DeepInfra's `gpt-oss-120b`. Set `DEEPINFRA_API_KEY` in your environment or store it in Secrets Manager and pass its ARN via `DeepinfraApiKeySecretArn`.

### Frontend (Next.js)

Prerequisites: Node 18+

```bash
cd frontend
npm install
NEXT_PUBLIC_API_BASE=http://localhost:8000 npm run dev
```

Visit <http://localhost:3000> to use the app.

## Tests

```bash
cd backend
pytest

cd ../frontend
npm run lint  # prints 'lint skipped'
```

## API

The local API exposes endpoints such as:

- `POST /upload-url` – obtain a pre‑signed S3 URL for PDF uploads.
- `POST /summaries` – start a summarization job.
- `GET /summaries/status?id=...` – poll job status.
- `GET /summaries/{id}` – fetch the finished summary.
- `POST /summaries/{id}/translate` – translate a summary.

Example:

```bash
curl -X POST http://localhost:8000/summaries \
  -H "content-type: application/json" \
  -d '{
    "input": {"url": "https://arxiv.org/pdf/1706.03762.pdf"},
    "mode": "micro",
    "privacy": "process-only"
  }'
```

## Architecture & Guardrails

- PDF files are stored in S3; metadata and summaries live in DynamoDB.
- Step Functions orchestrate the following Lambda tasks:
  1. `FetchMetadata`
  2. `ParseDocument`
  3. `PlanAndWrite`
  4. `EvidenceCheck`
  5. `Finalize`
- Each sentence in the summary links back to its source passage.
- Reading level and disclaimers are computed for the output.

## License

Apache-2.0

