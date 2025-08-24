# LayScience

LayScience is an AI-powered tool that turns research papers (PDF, DOI, or URL) into clear and trustworthy plain-language summaries. It can generate ultra-short "micro-stories" or more detailed write-ups. Built first for Kabul University female students—and for anyone who finds papers long, technical, or hard to follow—it aims to spark curiosity and make open science accessible.

### Features

- Summarise papers from a DOI, URL or uploaded PDF.
- Search arXiv by keyword and load papers by ID for summarisation.
- Choose between micro-stories or extended summaries, with optional detailed or humorous modes.
- Translate summaries into English, Persian, French, Spanish or German.
- Asynchronous FastAPI backend with job polling and SQLite storage.
- Next.js 14 frontend for submitting papers, registering accounts and leaving feedback.

The web app is live at [layscience.onrender.com](https://layscience.onrender.com/). You can run up to five summaries without an account; create a free account for unlimited use. If you're able, donations help cover hosting and API costs so the service stays available to those who can't afford much.

## Repository Structure

- `backend/` – FastAPI service that extracts paper text and calls OpenAI's GPT-5 Responses API.
- `frontend/` – Next.js 14 web app that provides the user interface.
- `data/` – Stores uploaded PDFs and a SQLite job database.

## Local Development

### Backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
export OPENAI_API_KEY=sk-...
uvicorn backend.server.main:app --reload
```

Additional environment variables such as `OPENAI_MODEL`, `ALLOWED_ORIGINS`, and SMTP settings are documented in [backend/README.md](backend/README.md).

### Frontend

```bash
cd frontend
npm install
export NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000
npm run dev
```

Open <http://localhost:3000> and enter a DOI/URL or upload a PDF to create a summary.

## Testing

Run the test suites before submitting changes:

```bash
pytest backend
cd frontend && npm test
```

## Deployment and Hosting

The production instance runs on [Render](https://render.com), which hosts the FastAPI backend and serves the Next.js frontend. Any platform that can build and run Docker or Node/Python apps (Render, Vercel, Netlify, etc.) can host LayScience. Ensure the environment variables listed above are set in your deployment environment.

## Contributing

Pull requests and issues are welcome. Please make sure the tests pass and follow the project coding style when contributing.

## License

This project is licensed under the [MIT License](LICENSE).

Created by Rashid Mushkani, 2025. For questions or feedback, contact [rashidmushkani@gmail.com](mailto:rashidmushkani@gmail.com).
