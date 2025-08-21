# LayScience Frontend (Next.js 14)

A minimal, stylish frontend that mirrors the look and feel in your screenshot (bold condensed header, grey gradient hero, thin lines background). It talks to the FastAPI backend.

## Quick start

```bash
cd frontend
npm i
# Point to backend
export NEXT_PUBLIC_API_BASE=http://localhost:8000
npm run dev
```

Open `http://localhost:3000`.

### Why this avoids “Failed to fetch”

- In **dev** we proxy all requests through `/api/proxy` to the backend specified in `NEXT_PUBLIC_API_BASE` to remove CORS issues.
- In **prod** you can set `NEXT_PUBLIC_API_BASE` to your API domain and also allow that origin on the backend using `ALLOWED_ORIGINS`.

### Environment variables

- `NEXT_PUBLIC_API_BASE` – URL of your backend (e.g. `http://localhost:8000` or `https://api.yourdomain.com`).

