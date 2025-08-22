
# LayScience Frontend — Fixed

Next.js 14 app that talks to the backend through an **edge proxy** at `/api/proxy/...`.

## Environment variables

Only the backend needs the OpenAI credentials. The frontend requires a single variable:

| Name | Purpose |
| --- | --- |
| `NEXT_PUBLIC_API_BASE` | Base URL of the backend API. Must be set in production deployments. |

If `NEXT_PUBLIC_API_BASE` is missing in production, the proxy route will respond with a helpful error instead of silently falling back to `127.0.0.1`.

## Local dev

```bash
cd frontend
npm install
# Or: pnpm install / yarn install
export NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000
npm run dev
```

Open http://localhost:3000 — enter a DOI or URL and/or upload a PDF, then click **Summarize**.

If you see a 404 or CORS error, verify:

- The backend is running at `NEXT_PUBLIC_API_BASE`.
- Backend `ALLOWED_ORIGINS` includes `http://localhost:3000`.
- The proxy path matches backend (`/api/v1/summaries` or `/summarize`; a legacy `/summarise` alias also exists).

## Deploy

Deploy the frontend (Vercel, Netlify, etc.) and set `NEXT_PUBLIC_API_BASE` to your backend URL.
