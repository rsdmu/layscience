# LayScience – Full Revised Code (Backend + Frontend)

This package contains a **complete, working** implementation of a paper summariser:

- **Backend** – FastAPI with robust CORS handling, PDF fetch/parsing, OpenAI-based summarisation + translation, proper error reporting and a health-check endpoint.
- **Frontend** – Next.js 14 with a clean UI inspired by your screenshot (bold condensed header, greyscale hero), a file drop zone, status polling and graceful error UX.

> This **replaces** the broken Lambda code (truncated headers, missing CORS, etc.) that frequently results in `TypeError: Failed to fetch`.  

---

## 1) Development – run everything locally

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Set env (use MOCK mode if you do not want to call the LLM)
export ALLOWED_ORIGINS=http://localhost:3000
export MOCK_SUMMARIZER=1
# or use a real LLM:
# export OPENAI_API_KEY=sk-...

uvicorn server.main:app --reload --port 8000
```

Open docs at <http://localhost:8000/docs>.

### Frontend

```bash
cd frontend
npm i

# Point to backend
export NEXT_PUBLIC_API_BASE=http://localhost:8000

npm run dev
```

Navigate to <http://localhost:3000> and try a DOI, a direct URL to a PDF, or upload a PDF.

---

## 2) Diagnostics – when you click *Summarise*

If you still encounter **“Failed to fetch”**, check these items:

1. **CORS**  
   - Backend `ALLOWED_ORIGINS` must include the origin of the frontend.  
   - In dev we proxy via `/api/proxy`, so set `NEXT_PUBLIC_API_BASE` and you avoid CORS entirely.

2. **HTTP/HTTPS mismatch**  
   - Browsers block mixed content (`https` page calling `http` API). Use HTTPS on both or use the proxy.

3. **Incorrect API base**  
   - Confirm `NEXT_PUBLIC_API_BASE` points to the backend (`curl $NEXT_PUBLIC_API_BASE/api/v1/health` should return `{ "ok": true }`).

4. **Server errors**  
   - Check backend logs. The API consistently returns JSON with the right status codes; crashes are logged with stack traces.

5. **Preflight failures**  
   - We only send standard `Content-Type: application/json` and `multipart/form-data`, which are CORS-simple. Preflight should pass.

6. **Large files**  
   - If the uploaded file is too large for your host, increase reverse-proxy limits (nginx `client_max_body_size`, etc.).

---

## 3) Production deployment options

### Option A – Docker (single VM or ECS/Fargate)

**Backend**

```bash
cd backend
docker build -t layscience-backend .
docker run -d --name layscience-backend -p 8000:8000 \
  -e ALLOWED_ORIGINS=https://your-frontend.example \
  -e OPENAI_API_KEY=sk-... \
  ghcr.io/your-org/layscience-backend:latest
```

Put it behind your HTTPS ingress and point `NEXT_PUBLIC_API_BASE` to it.

**Frontend**

- Deploy to Vercel/Netlify/Render or any static host:
  - Set env var `NEXT_PUBLIC_API_BASE=https://api.yourdomain.com`
  - Build: `npm run build`
  - Start: `npm run start`

### Option B – Vercel (frontend) + Render/Fly (backend)

- Backend: deploy Docker image to Render or Fly.io.   
- Frontend: deploy repo to Vercel, set `NEXT_PUBLIC_API_BASE` to backend public URL.
- Backend `ALLOWED_ORIGINS` must include the Vercel domain.

### Option C – AWS (API Gateway + Lambda) [simple path]

If you prefer Lambda:
- Wrap the FastAPI app with Mangum (ASGI adapter) and deploy under Lambda + API Gateway.
- Keep the same endpoints and CORS settings.
- Update `NEXT_PUBLIC_API_BASE` to the API Gateway URL.

> This path is dramatically simpler than a Step Functions pipeline and removes an entire class of failures.

---

## 4) File layout

```
revised/
├── backend
│   ├── Dockerfile
│   ├── README.md
│   ├── requirements.txt
│   └── server
│       ├── main.py
│       └── services
│           ├── jobs.py
│           ├── pdfio.py
│           ├── storage.py
│           ├── summarizer.py
│           └── translator.py
└── frontend
    ├── app
    │   ├── api/proxy/route.ts
    │   ├── layout.tsx
    │   └── page.tsx
    ├── components
    │   ├── Dropzone.tsx
    │   ├── Hero.tsx
    │   ├── SummaryCard.tsx
    │   └── ui
    │       ├── Button.tsx
    │       └── Progress.tsx
    ├── lib/api.ts
    ├── styles/globals.css
    ├── package.json
    └── tailwind.config.js
```

---

## 5) Security and best practices

- CORS is **explicit** and configurable.
- All endpoints validate input and return informative errors.
- LLM calls are **sandboxed** with low temperature and JSON response format.
- Background tasks are kept **in-process** (simple, observable). Scale by deploying multiple instances behind a queue if needed.
- Logs are structured; add your own logger sink (Datadog, CloudWatch) as required.

---

## 6) Extending

- Swap the summariser model: set `OPENAI_MODEL` or replace `services/summarizer.py`.
- Replace storage with S3: create an `/api/v1/uploads/sign` endpoint and upload to S3; the rest of the code remains the same.
- Add authentication: protect `/api/v1/jobs` and `/api/v1/upload` with a token (e.g. JWT) and enforce it in a middleware.

Enjoy!
