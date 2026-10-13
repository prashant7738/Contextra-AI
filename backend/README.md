# Contextra AI Backend

## Environment Variables

Configure via `.env` file:

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | Yes | — | PostgreSQL connection string (e.g. `postgresql+psycopg2://user:pass@localhost:5432/contextra`) |
| `OPENAI_API_KEY` | Yes | — | OpenAI API key, used for the `gpt-6-luna` LLM and `text-embedding-3-small` embeddings |
| `DAILY_BUDGET_USD` | No | `0.25` | Global OpenAI spend cap per UTC day, shared by all users. Requests get a 429 once it is reached |
| `SECRET_KEY` | Yes | — | JWT signing secret |
| `ADMIN_EMAIL` | No | — | Email of the admin user (admin endpoints require this) |
| `CRON_SECRET` | No | — | Secret for `/cron/run` endpoint |
| `CORS_ORIGINS` | No | `http://localhost:3000,http://localhost:4321,https://contextra-ai.vercel.app` | Comma-separated allowed CORS origins |
| `ALGORITHM` | No | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `30` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | `7` | Refresh token lifetime |
| `SUPABASE_URL` | No | — | Supabase Storage URL (optional) |
| `SUPABASE_SERVICE_ROLE_KEY` | No | — | Supabase Storage service role key |
| `SUPABASE_STORAGE_BUCKET` | No | `documents` | Supabase Storage bucket name |
| `DEFAULT_USER_BUDGET_USD` | No | `1.0` | Default monthly OpenAI spend (USD) per user |

---

## Authentication Endpoints

All auth endpoints are prefixed with `/auth`.

### POST `/auth/register`
Register a user with name, email, and password.

```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "password": "StrongPass123!"
  }'
```

**Response:**
```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "name": "John Doe",
    "email": "john@example.com",
    "budget_usd": 1.0,
    "spent_usd": 0.0
  }
}
```

---

### POST `/auth/login`
Login with email and password.

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "StrongPass123!"
  }'
```

---

### POST `/auth/refresh`
Get a new access token using a refresh token.

```bash
curl -X POST "http://localhost:8000/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "your_refresh_token"
  }'
```

---

### GET `/auth/me`
Get currently authenticated user details.

```bash
curl "http://localhost:8000/auth/me" \
  -H "Authorization: Bearer your_access_token"
```

---

## Admin Endpoints

Admin endpoints are prefixed with `/admin`. All require authentication and the user's email must match the `ADMIN_EMAIL` env var.

### GET `/admin/users`
List all users (admin-only).

### PATCH `/admin/users/{user_id}/budget`
Update a user's monthly OpenAI budget in USD.

```bash
curl -X PATCH "http://localhost:8000/admin/users/1/budget" \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{"budget_usd": 5.0}'
```

### GET `/admin/users/{user_id}/chats`
List all chats for a specific user.

### GET `/admin/chats/{chat_id}/messages`
View all messages for a chat (bypasses ownership).

---

## Chat Management Endpoints

All chat endpoints are prefixed with `/chats` and require authentication.

### POST `/chats/`
Create a new chat for a user.

```bash
curl -X POST "http://localhost:8000/chats/?user_id=1" \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{"name": "Document Analysis"}'
```

**Response:**
```json
{
  "id": 1,
  "local_id": 1,
  "user_id": 1,
  "name": "Document Analysis",
  "created_at": "2026-05-26T12:00:00",
  "updated_at": "2026-05-26T12:00:00"
}
```

### GET `/chats/`
List all chats for a user.

```bash
curl "http://localhost:8000/chats/?user_id=1" \
  -H "Authorization: Bearer your_token"
```

### GET `/chats/{chat_id}`
Get a specific chat (verifies ownership).

```bash
curl "http://localhost:8000/chats/1?user_id=1" \
  -H "Authorization: Bearer your_token"
```

### PATCH `/chats/{chat_id}`
Update a chat's name (verifies ownership).

```bash
curl -X PATCH "http://localhost:8000/chats/1?user_id=1" \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{"name": "Updated Name"}'
```

### DELETE `/chats/{chat_id}`
Delete a chat (verifies ownership).

```bash
curl -X DELETE "http://localhost:8000/chats/1?user_id=1" \
  -H "Authorization: Bearer your_token"
```

### GET `/chats/{chat_id}/messages`
Get recent conversation history for a chat.

```bash
curl "http://localhost:8000/chats/1/messages?user_id=1&limit=50" \
  -H "Authorization: Bearer your_token"
```

**Parameters:**
- `user_id` (query): ID of the chat owner
- `limit` (query, optional): Number of recent messages to return (1-200, default: 50)

---

### POST `/chats/query`
Ask a question within a specific chat context.

```bash
curl -X POST "http://localhost:8000/chats/query?user_id=1" \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": 1,
    "request": "What is the main topic of the document?"
  }'
```

**Response:**
```json
{
  "answer": "Based on the documents in this chat, the main topic is... [AI-generated answer]",
  "references": [
    {
      "filename": "doc.pdf",
      "page": 3,
      "document_id": 1
    }
  ],
  "conversation_history": [
    {
      "id": 1,
      "chat_id": 1,
      "user_message": "What is the main topic?",
      "bot_response": "The main topic is...",
      "created_at": "2026-05-26T12:00:00"
    }
  ]
}
```

**How it works:**
1. Verifies chat ownership
2. Embeds the question
3. Finds top-10 similar chunks from the chat
4. Includes previous conversation context (last 10 messages)
5. Passes context to gpt-6-luna
6. Saves message & response to history
7. Returns answer, references, and conversation history
8. Charges the real OpenAI cost to the user's monthly USD budget

---

### POST `/chats/detailed-summarizer`
Generate a detailed study summary using the 80/20 rule from uploaded documents in a chat.

```bash
curl -X POST "http://localhost:8000/chats/detailed-summarizer?user_id=1" \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": 1,
    "topic_name": "Machine Learning",
    "n_results": 5,
    "max_tokens": 700
  }'
```

**Parameters:**
- `user_id` (query): ID of the user
- `chat_id` (body): ID of the chat to summarize
- `topic_name` (body, default: `"all"`): Topic to summarize; use `"all"` for full context
- `n_results` (body, optional, default: 5, range: 3-40): Number of relevant chunks
- `max_tokens` (body, optional, default: 700, range: 200-1200): Max tokens for response

**Response:**
```json
{
  "summary": "... [detailed 80/20 summary text]",
  "topic": "Machine Learning",
  "references": [
    {
      "filename": "ai_book.pdf",
      "page": 1,
      "document_id": 1
    }
  ],
  "chunks_used": 15,
  "title": "Machine Learning Fundamentals",
  "sections": [
    {
      "heading": "Core Concepts",
      "items": [
        "ML is a subset of AI that enables systems to learn from data...",
        "Supervised learning uses labeled training data..."
      ]
    },
    {
      "heading": "Must Remember",
      "items": [
        "Bias-variance tradeoff is key to model performance",
        "Overfitting occurs when model memorizes noise"
      ]
    },
    {
      "heading": "Quick Revision Checklist",
      "items": [
        "Understand difference between supervised/unsupervised/reinforcement learning",
        "Know key evaluation metrics (accuracy, precision, recall, F1)"
      ]
    }
  ]
}
```

### POST `/chats/summary-task`
Create an asynchronous summary task (non-blocking alternative to `/chats/detailed-summarizer`).

```bash
curl -X POST "http://localhost:8000/chats/summary-task?user_id=1" \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{"chat_id": 1, "topic_name": "Machine Learning"}'
```

**Response:** `{"task_id": "uuid-string"}`

### GET `/chats/summary-task/{task_id}`
Get the status and result of an async summary task.

```bash
curl "http://localhost:8000/chats/summary-task/uuid-string" \
  -H "Authorization: Bearer your_token"
```

**Response (pending):**
```json
{"task_id": "uuid-string", "status": "pending", "result": null, "error": null}
```

**Response (done):**
```json
{
  "task_id": "uuid-string",
  "status": "done",
  "result": { "summary": "...", "topic": "all", "references": [], "chunks_used": 10, "title": "...", "sections": [] },
  "error": null
}
```

---

### POST `/chats/flashcard`
Generate intelligent flashcards from all uploaded documents in a chat.

```bash
curl -X POST "http://localhost:8000/chats/flashcard?user_id=1&chat_id=1" \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{"n_results": 5, "max_tokens": 1000}'
```

**Parameters:**
- `user_id` (query): ID of the user
- `chat_id` (query): ID of the chat
- `n_results` (body, optional, default: 5, range: 3-40): Number of relevant chunks
- `max_tokens` (body, optional, default: 1000, range: 500-2000): Max tokens for generation

**Response:**
```json
{
  "flashcards": [
    {
      "topic": "Machine Learning Basics",
      "summary": "ML is a subset of AI that enables systems to learn from data",
      "explanation": "Machine Learning is a branch of Artificial Intelligence...",
      "references": [
        { "filename": "ai_book.pdf", "page": 5, "document_id": 1 }
      ]
    }
  ],
  "total_topics": 8,
  "total_flashcards": 32
}
```

**Flashcard Generation Features:**
- **Smart Distribution**: Important topics get 8-12 flashcards, medium 4-7, basic 2-3
- **Comprehensive Content**: Topic name, one-line summary, detailed explanation
- **Source Tracking**: References to source documents for each flashcard
- **Full Context**: Always uses ALL uploaded documents in the chat

---

## Document Management Endpoints

All document endpoints are prefixed with `/documents` and require authentication.

### GET `/documents/`
List all documents for a specific chat.

```bash
curl "http://localhost:8000/documents/?user_id=1&chat_id=1" \
  -H "Authorization: Bearer your_token"
```

**Response:**
```json
[
  { "id": 1, "chat_id": 1, "filename": "ai_book.pdf" }
]
```

### POST `/documents/ingest/direct`
Upload a PDF directly (file body).

```bash
curl -X POST "http://localhost:8000/documents/ingest/direct?user_id=1&chat_id=1" \
  -H "Authorization: Bearer your_token" \
  -F "file=@document.pdf"
```

**Parameters:**
- `user_id` (query): ID of the user
- `chat_id` (query): ID of the chat
- `use_ocr` (query, optional, default: `false`): Enable OCR for scanned PDFs
- `file` or `files` (form-data): PDF file(s)

**Response:**
```json
{
  "task_id": 1,
  "status": "pending"
}
```

### POST `/documents/ingest/presign`
Get a presigned upload URL for client-side upload (used with Supabase Storage).

```bash
curl -X POST "http://localhost:8000/documents/ingest/presign?user_id=1&chat_id=1" \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{"filename": "document.pdf"}'
```

**Response:**
```json
{
  "task_id": 1,
  "upload_url": "https://storage.supabase.co/...",
  "upload_method": "PUT"
}
```

### POST `/documents/ingest/{task_id}/confirm`
Confirm upload and trigger background ingestion.

```bash
curl -X POST "http://localhost:8000/documents/ingest/1/confirm?user_id=1" \
  -H "Authorization: Bearer your_token"
```

### GET `/documents/ingest/status/{task_id}`
Check the status of an ingestion task.

```bash
curl "http://localhost:8000/documents/ingest/status/1?user_id=1" \
  -H "Authorization: Bearer your_token"
```

**Response:**
```json
{
  "task_id": 1,
  "status": "completed",
  "chunks_count": 25,
  "error_message": null,
  "created_at": "2026-05-26T12:00:00",
  "updated_at": "2026-05-26T12:00:05"
}
```

**Ingestion Flow:**
1. Upload PDF via `/ingest/direct` (direct) or `/ingest/presign` + `/ingest/{id}/confirm` (presigned)
2. Background task processes the file:
   - Extracts text from PDF using PyMuPDF (with optional EasyOCR fallback for scanned pages)
   - Chunks text into smaller pieces (~300 words each)
   - Creates embeddings for each chunk
   - Stores chunks in pgvector (PostgreSQL + vector extension)
3. Poll `/ingest/status/{task_id}` until `status` is `completed` or `error`

---

## Cron Endpoints

### POST `/cron/run`
Trigger maintenance jobs (requires `CRON_SECRET` header).

```bash
curl -X POST "http://localhost:8000/cron/run" \
  -H "X-Cron-Secret: your_secret"
```

---

## Root Endpoint

### GET `/`
Health check.

```bash
curl "http://localhost:8000/"
```

**Response:**
```json
{
  "message": "Hello from Second Brain AI",
  "step": 2
}
```

---

## Complete Workflow Example

### Step 1: Register / Login
```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice", "email": "alice@example.com", "password": "SecurePass1!"}'
# Save the access_token from response
```

### Step 2: Create Chat
```bash
curl -X POST "http://localhost:8000/chats/?user_id=1" \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{"name": "AI Research"}'
```

### Step 3: Upload Document
```bash
curl -X POST "http://localhost:8000/documents/ingest/direct?user_id=1&chat_id=1" \
  -H "Authorization: Bearer your_token" \
  -F "file=@ai_research.pdf"
# Response: {"task_id": 1, "status": "pending"}
```

### Step 4: Wait for Ingestion
```bash
curl "http://localhost:8000/documents/ingest/status/1?user_id=1" \
  -H "Authorization: Bearer your_token"
# Repeat until status is "completed"
```

### Step 5: Query the Chat
```bash
curl -X POST "http://localhost:8000/chats/query?user_id=1" \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{"chat_id": 1, "request": "What are the key findings?"}'
```

### Step 6: Generate Summary (Optional)
```bash
curl -X POST "http://localhost:8000/chats/detailed-summarizer?user_id=1" \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{"chat_id": 1, "topic_name": "AI Research"}'
```

### Step 7: Generate Flashcards (Optional)
```bash
curl -X POST "http://localhost:8000/chats/flashcard?user_id=1&chat_id=1" \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

## Architecture Overview

### Data Flow

```
1. PDF Upload (Direct or Presigned)
   └─> Background task → Extract text (PyMuPDF + optional OCR) 
       → Chunk text (~300 words) → Embed chunks (384-dim) 
       → Store in pgvector (PostgreSQL)

2. Query & Chat
   └─> Embed question → Find top-10 similar chunks (pgvector cosine search)
       → Include last 10 messages as conversation context
       → Pass to gpt-6-luna → Return answer + references + history
       → Charge actual OpenAI cost to user's monthly USD budget

3. Detailed Summarization (80/20)
   └─> If specific topic → first answer_query for LLM-enriched context
       → Retrieve relevant chunks → Generate structured JSON summary
       → Return with title, sections (Core Concepts / Must Remember / Checklist), references

4. Flashcard Generation
   └─> Retrieve all context → LLM generates flashcards in structured format
       → Parse output → Return organized set with topic distribution

5. Async Tasks
   └─> Summary tasks run in background thread with DB status tracking
       → Poll /summary-task/{id} for completion

6. Isolation
   └─> All operations verify user_id matches current_user.id from JWT
       → Admin endpoints gated by ADMIN_EMAIL match
```

### Technology Stack

- **Framework**: FastAPI (Python 3.12+)
- **Database**: PostgreSQL + pgvector (vector extension)
- **Embedding Model**: OpenAI `text-embedding-3-small` (requested at 384 dimensions to match the `Vector(384)` column)
- **LLM**: OpenAI `gpt-6-luna` only, with no fallback model
- **Spend cap**: global daily USD budget (`DAILY_BUDGET_USD`, default $0.25). Each OpenAI call reserves its worst-case cost, then settles to the real usage. `GET /admin/spend` shows today's spend
- **PDF Extraction**: PyMuPDF (text) + EasyOCR (scanned page fallback)
- **ORM**: SQLAlchemy 2.0
- **Migrations**: Alembic
- **Auth**: JWT (python-jose) with access + refresh tokens
- **Password Hashing**: bcrypt (via passlib)
- **Storage**: Local temp files or Supabase Storage (optional)
- **Spend Budget**: Monthly per-user OpenAI spend (USD) tracking

---

## Error Handling

### Common Errors

**403 Forbidden - User mismatch:**
```bash
curl "http://localhost:8000/chats/999?user_id=1" \
  -H "Authorization: Bearer your_token"
# Response: {"detail": "Forbidden: user mismatch"}
```

**404 Not Found - Chat doesn't belong to user:**
```bash
curl "http://localhost:8000/chats/999?user_id=1" \
  -H "Authorization: Bearer your_token"
# Response: {"detail": "Chat not found or doesn't belong to you"}
```

**422 Validation Error - Missing required field:**
```bash
curl -X POST "http://localhost:8000/chats/?user_id=1" \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{}'
# Response: {"detail": [{"loc": ["body", "name"], "msg": "field required", ...}]}
```

**500 Error - Processing failed:**
```bash
# Response: {"detail": "Error processing query: ..."}
```

---

## Development

### Setup

```bash
# Create virtual environment
uv venv
source .venv/bin/activate

# Install dependencies
uv sync

# Copy env file
cp .env.example .env
# Edit .env with your database URL and HF token

# Run database migrations
uv run alembic upgrade head

# Start server
uv run uvicorn app.main:app --reload
```

### Clear Database

```bash
uv run python3 << 'EOF'
from app.database import Base, engine
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
print("✓ Database cleared")
EOF
```

### Run Tests

```bash
# (Add tests as needed)
```

### Migrations

```bash
# Create new migration
uv run alembic revision --autogenerate -m "description"

# Apply migrations
uv run alembic upgrade head

# Rollback
uv run alembic downgrade -1
```

---

## Production Considerations

- Use a connection pooler (e.g. PgBouncer) for PostgreSQL
- Implement rate limiting
- Add comprehensive logging (structured logging)
- Use HTTPS
- Deploy with Docker/Kubernetes
- Set up proper backups for PostgreSQL
- Monitor vector search latency and token usage
- Configure Supabase Storage or S3 for file persistence

---

## Troubleshooting

### OpenAI Key or Budget Issues
```bash
# Set your key in .env (never commit it)
OPENAI_API_KEY=your_key_here

# Check today's spend (admin only)
GET /admin/spend
```
A `429 Daily AI budget reached` response means the global cap was hit. It resets at 00:00 UTC, or raise `DAILY_BUDGET_USD`.

### PostgreSQL Connection Failed
```bash
# Check PostgreSQL is running
psql -U postgres -c "SELECT 1;"

# Verify connection string in .env
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/contextra

# Ensure pgvector extension is installed
psql -U postgres -d contextra -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### Re-embedding Existing Documents
Documents ingested before the OpenAI switch have BGE vectors, which can't be compared with OpenAI vectors. Re-embed them once (resumable, counts against the daily budget):
```bash
python -m scripts.reembed_all
```

---

## Future Enhancements

- [ ] Support for more file formats (docx, txt, images with OCR)
- [ ] Hybrid search (BM25 + semantic)
- [ ] Document metadata editing
- [ ] Chat history export
- [ ] Streaming responses
- [ ] Multi-language support
- [ ] Fine-tuned embedding models per domain

---

## License

MIT

## Support

For issues or questions, please open an issue in the repository.
