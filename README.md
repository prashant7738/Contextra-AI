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
| Astro 6 + React 18 | FastAPI (Python 3.12) | Gemini (fallback: Llama 3.1 8B via HuggingFace) | PostgreSQL + pgvector |
| TypeScript, Vite | SQLAlchemy, Alembic | BGE-small embeddings | Supabase |
| Custom design system | JWT auth, bcrypt | Hybrid OCR (fitz + EasyOCR) | — |

---

## Quick start

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add DATABASE_URL, GEMINI_API_KEY, HF_TOKEN, SECRET_KEY, ADMIN_EMAIL
alembic upgrade head
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

**Required:** `DATABASE_URL`, `HF_TOKEN`, `SECRET_KEY`, `ADMIN_EMAIL`, `CRON_SECRET` (optional: `GEMINI_API_KEY` for the primary LLM provider)

**Optional:** `OPENAI_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `DEFAULT_USER_TOKEN_LIMIT`

Full reference in `backend/.env.example` and `frontend/.env.example`.

---

## Who it's for

- **Students** — upload lecture notes, generate summaries and flashcards before exams
- **Researchers** — process papers, extract findings, build a searchable knowledge base
- **Professionals** — internal docs, training materials, technical manuals — ask instead of search
- **Self-learners** — your personal second brain for any topic you're diving into

---

## License

MIT
