# Contextra AI

**Your documents, supercharged. Chat, summarize, and memorize — like a second brain that actually works.**

Stop drowning in PDFs. Contextra AI ingests your documents and turns them into an interactive knowledge base you can talk to. Ask questions, get 80/20 summaries(Pareto Principle), generate flashcards — all grounded in your own files.

---

## What it does

### Chat with your documents
Upload any PDF. Ask questions in plain English. Contextra AI finds the most relevant passages using vector search and answers with citations back to your sources. No hallucinations — everything is anchored to your material.

### Pareto Insight (80/20 summaries)
Feed it a semester's worth of notes. Get back the 20% that carries 80% of the value: core concepts, must-remember items, and a revision checklist. Pick a specific topic or summarize everything at once.

### Intelligent flashcards
Turn any document set into a deck of smart flashcards — topic, one-line summary, detailed explanation, and source references. Collapsible UI, expandable explanations, generated in seconds.

### Multi-chat workspace
Keep projects, courses, and research silos separate. Each chat has its own documents, conversation history, and generated content. Create, rename, delete — full control.

---

## Tech stack

| Frontend | Backend | AI | Database |
|---|---|---|---|
| Astro 6 + React 18 | FastAPI (Python 3.12) | OpenAI gpt-6-luna (chat, summaries, flashcards) | PostgreSQL + pgvector |
| TypeScript, Vite | SQLAlchemy, Alembic | OpenAI text-embedding-3-small embeddings | Supabase |
| Custom design system | JWT auth, bcrypt | Hybrid OCR (fitz + EasyOCR) | — |

---

## Quick start

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt   # runtime deps + pytest
# Optional OCR for scanned PDFs (installs CPU PyTorch, needs ~2 GB RAM):
# pip install -r requirements-ocr.txt
cp .env.example .env   # add DATABASE_URL, OPENAI_API_KEY, SECRET_KEY, ADMIN_EMAIL
alembic upgrade head   # the schema is managed only by Alembic
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm ci
cp .env.example .env   # set PUBLIC_API_BASE_URL=http://localhost:8000
npm run dev
```

---

## Environment variables

**Required:** `DATABASE_URL`, `OPENAI_API_KEY`, `SECRET_KEY`, `ADMIN_EMAIL`, `CRON_SECRET`

**Optional:** `DAILY_BUDGET_USD` (global AI spend cap per UTC day, default `0.25`), `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `DEFAULT_USER_BUDGET_USD` (monthly per-user OpenAI spend cap in USD, default `1.0`)

Full reference in `backend/.env.example` and `frontend/.env.example`.

> **Admin account:** admin rights belong to whoever registers `ADMIN_EMAIL` (there is no email verification). Register that account yourself right after the first deploy.

---

## Tests

```bash
cd backend && python -m pytest -q        # unit tests; no database needed
# Integration tests run too when DATABASE_URL points at a migrated
# PostgreSQL + pgvector database (otherwise they are skipped).

cd frontend && npm test && npm run check && npm run build
```

CI (`.github/workflows/ci.yml`) runs all of the above on every pull request, including `alembic upgrade head` against a fresh pgvector database.

## Deployment

- **Backend (Render):** `render.yaml` builds with `pip install -r requirements.txt` and starts with `alembic upgrade head && uvicorn ...`, so migrations are applied on every deploy. If the service was created by hand rather than from the blueprint, set the same Start Command in the Render dashboard.
- **Frontend (Vercel):** static Astro build (`npm run build`, output `dist`).
- Health checks: `GET /health` (liveness, no dependencies) and `GET /health/ready` (checks the database).

---

## Who it's for

- **Students** — upload lecture notes, generate summaries and flashcards before exams
- **Researchers** — process papers, extract findings, build a searchable knowledge base
- **Professionals** — internal docs, training materials, technical manuals — ask instead of search
- **Self-learners** — your personal second brain for any topic you're diving into

---

## License

MIT
