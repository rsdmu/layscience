# LayScience Frontend (fixed)

This is a robust Next.js 14 + Tailwind app that talks to your FastAPI backend.
It uses a dev **proxy** to avoid CORS headaches and CommonJS configs for PostCSS/Tailwind to avoid the `SyntaxError: Unexpected token 'export'` you saw.

## Quick start

```bash
# Node 18.17+ or 20 LTS recommended
cd frontend
npm i
echo "NEXT_PUBLIC_API_BASE=http://localhost:8000" > .env.local
npm run dev
```

Open http://localhost:3000 and test:
- Enter DOI or a direct PDF URL or upload a PDF.
- Click **Summarise**.

## Notes

- We use CommonJS for `postcss.config.js` and `tailwind.config.js` because Next loads PostCSS config via `require()`.
- `app/api/proxy/[...path]` forwards all requests to `NEXT_PUBLIC_API_BASE` so local dev does not rely on CORS.
- If you previously had `postcss.config.mjs` or an ESM `postcss.config.js`, **delete** it and use this one.
- If a previous `.next` cache exists, clear it: `rm -rf .next node_modules && npm i`.
