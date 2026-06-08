# Contextra AI Backend
## User Management

Public `/users` management endpoints have been removed. User creation and authentication continue to be handled by the `/auth` routes (login/refresh/me). Administrators can manage and inspect users via the admin endpoints:

- `GET /admin/users` — list all users (admin-only)
- `GET /admin/users/{user_id}/chats` — list a user's chats (admin-only)
- `GET /admin/chats/{chat_id}/messages` — view messages for a chat (admin-only)

Configure the admin account email using the `ADMIN_EMAIL` environment variable (see Environment Variables above).
**Response:**
```json
{
  "message": "Hello from Second Brain AI",
  "step": 2
}
```

---

## Authentication Endpoints

### 2. Register User

#### POST `/auth/register`
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
    "email": "john@example.com"
  }
}
```

---

### 3. Login

#### POST `/auth/login`
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

### 4. Refresh Access Token

#### POST `/auth/refresh`
Get a new access token using a refresh token.

```bash
curl -X POST "http://localhost:8000/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "your_refresh_token"
  }'
```

---

### 5. Get Current User

#### GET `/auth/me`
Get currently authenticated user details.

```bash
curl "http://localhost:8000/auth/me" \
  -H "Authorization: Bearer your_access_token"
```

---

## User Management Endpoints

### 6. Create User

#### POST `/users/`
Create a new user.

```bash
curl -X POST "http://localhost:8000/users/" \
  -H "Content-Type: application/json" \
  -d '{"name": "John Doe"}'
```

**Response:**
```json
{
  "id": 1,
  "name": "John Doe"
}
```

---

### 7. List All Users

#### GET `/users/`
Get all users with pagination.

```bash
curl "http://localhost:8000/users/?skip=0&limit=100"
```

**Response:**
```json
[
  {
    "id": 1,
    "name": "John Doe"
  },
  {
    "id": 2,
    "name": "Jane Smith"
  }
]
```

---

### 8. Get Specific User

#### GET `/users/{user_id}`
Get user details by ID.

```bash
curl "http://localhost:8000/users/1"
```

**Response:**
```json
{
  "id": 1,
  "name": "John Doe"
}
```

---

### 9. Delete User

#### DELETE `/users/{user_id}`
Delete a user by ID.

```bash
curl -X DELETE "http://localhost:8000/users/1"
```

**Response:**
```json
{
  "ok": true
}
```

---

## Chat Management Endpoints

### 10. Get Chat Messages

#### GET `/chats/{chat_id}/messages`
Get recent conversation history for a chat.

```bash
curl "http://localhost:8000/chats/1/messages?user_id=1&limit=50"
```

**Parameters:**
- `user_id` (query): ID of the chat owner
- `limit` (query, optional): Number of recent messages to return (1-200, default: 50)

---

### 11. Create Chat

#### POST `/chats/`
Create a new chat for a user.

```bash
curl -X POST "http://localhost:8000/chats/?user_id=1" \
  -H "Content-Type: application/json" \
  -d '{"name": "Document Analysis"}'
```

**Response:**
```json
{
  "id": 1,
  "user_id": 1,
  "name": "Document Analysis",
  "created_at": "2026-05-26T12:00:00",
  "updated_at": "2026-05-26T12:00:00"
}
```

---

### 12. List User's Chats

#### GET `/chats/`
Get all chats for a specific user.

```bash
curl "http://localhost:8000/chats/?user_id=1"
```

**Response:**
```json
[
  {
    "id": 1,
    "user_id": 1,
    "name": "Document Analysis",
    "created_at": "2026-05-26T12:00:00",
    "updated_at": "2026-05-26T12:00:00"
  },
  {
    "id": 2,
    "user_id": 1,
    "name": "Research Chat",
    "created_at": "2026-05-26T12:05:00",
    "updated_at": "2026-05-26T12:05:00"
  }
]
```

---

### 13. Get Specific Chat

#### GET `/chats/{chat_id}`
Get a specific chat (verifies ownership).

```bash
curl "http://localhost:8000/chats/1?user_id=1"
```

**Response:**
```json
{
  "id": 1,
  "user_id": 1,
  "name": "Document Analysis",
  "created_at": "2026-05-26T12:00:00",
  "updated_at": "2026-05-26T12:00:00"
}
```

---

### 14. Delete Chat

#### DELETE `/chats/{chat_id}`
Delete a chat (verifies ownership).

```bash
curl -X DELETE "http://localhost:8000/chats/1?user_id=1"
```

**Response:**
```json
{
  "ok": true
}
```

---

## Document Management Endpoints

### 15. Upload Document to Chat

#### POST `/documents/ingest`
Upload and ingest a PDF document into a specific chat.

```bash
curl -X POST "http://localhost:8000/documents/ingest?user_id=1&chat_id=1" \
  -F "files=@document.pdf"
```

**Parameters:**
- `user_id` (query): ID of the user uploading the document
- `chat_id` (query): ID of the chat to attach the document to
- `files` (form-data): PDF file(s) to upload (repeat field for multiple files)

**Response:**
```json
{
  "chunks_count": 25,
  "status": "embedded and stored",
  "document_id": 1,
  "chat_id": 1
}
```

**Notes:**
- Extracts text from PDF
- Chunks text into smaller pieces
- Creates embeddings for each chunk
- Stores chunks in both PostgreSQL and ChromaDB
- Only documents uploaded to a chat are searchable in that chat

---

## Chat Query Endpoint

### 16. Query Within Chat

#### POST `/chats/query`
Ask a question within a specific chat context.

```bash
curl -X POST "http://localhost:8000/chats/query?user_id=1" \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": 1,
    "request": "What is the main topic of the document?"
  }'
```

**Parameters:**
- `user_id` (query): ID of the user asking the query
- `chat_id` (body): ID of the chat to search within
- `request` (body): The question to ask

**Response:**
```json
{
  "answer": "Based on the documents in this chat, the main topic is... [AI-generated answer]"
}
```

**How it works:**
1. Verifies chat ownership (user can only query their own chats)
2. Embeds the question using the same model as the chunks
3. Finds top-3 similar chunks from the chat
4. Passes the context to Llama 3.1 8B
5. Returns the generated answer

---

### 17. Generate Detailed Study Summary

#### POST `/chats/detailed-summarizer`
Generate a detailed study summary using the 80/20 rule from uploaded documents in a chat.

```bash
curl -X POST "http://localhost:8000/chats/detailed-summarizer?user_id=1" \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": 1,
    "topic_name": "Machine Learning",
    "n_results": 5,
    "max_tokens": 2000
  }'
```

**Parameters:**
- `user_id` (query): ID of the user requesting the summary
- `chat_id` (body): ID of the chat to summarize
- `topic_name` (body): Topic to summarize (use "all" or leave empty for full context summary)
- `n_results` (body): Number of relevant chunks to retrieve (optional)
- `max_tokens` (body): Maximum tokens for the response (optional)

**Response:**
```json
{
  "summary": "Machine Learning is a subset of AI that enables systems to learn and improve from experience... [Detailed 80/20 summary]",
  "topic": "Machine Learning",
  "references": [
    {
      "page": 1,
      "document_id": 1,
      "document_name": "ai_book.pdf"
    }
  ],
  "chunks_used": 15
}
```

**How it works:**
1. Verifies chat ownership
2. If topic is specific, first retrieves LLM-enriched context via query
3. Generates a concise summary following the 80/20 Pareto principle (80% value in 20% content)
4. Includes references to source documents and chunks used

---

### 18. Generate Flashcards

#### POST `/chats/flashcard`
Generate intelligent flashcards from all uploaded documents in a chat.

```bash
curl -X POST "http://localhost:8000/chats/flashcard?user_id=1&chat_id=1" \
  -H "Content-Type: application/json" \
  -d '{
    "n_results": 5,
    "max_tokens": 1000
  }'
```

**Parameters:**
- `user_id` (query): ID of the user requesting flashcards
- `chat_id` (query): ID of the chat to generate flashcards from
- `n_results` (body, optional): Number of relevant chunks to retrieve for generation (default: 5)
- `max_tokens` (body, optional): Maximum tokens for generation (default: 1000)

**Response:**
```json
{
  "flashcards": [
    {
      "topic": "Machine Learning Basics",
      "summary": "ML is a subset of AI that enables systems to learn from data",
      "explanation": "Machine Learning is a branch of Artificial Intelligence that focuses on enabling computer systems to automatically learn and improve from experience without being explicitly programmed. It uses algorithms to find patterns in data and make predictions or decisions based on those patterns.",
      "references": [
        {
          "page": 5,
          "document_id": 1,
          "document_name": "ai_book.pdf"
        }
      ]
    },
    {
      "topic": "Neural Networks",
      "summary": "Neural networks mimic biological neurons to process information",
      "explanation": "...",
      "references": [...]
    }
  ],
  "total_topics": 8,
  "total_flashcards": 32
}
```

**Flashcard Generation Features:**
- **Smart Distribution**: Automatically creates more flashcards for important topics (8-12), medium topics (4-7), and basic topics (2-3)
- **Comprehensive Content**: Each flashcard includes topic name, one-line summary, and detailed explanation
- **Source Tracking**: References to source documents for each flashcard
- **Full Context**: Always uses ALL uploaded documents in the chat (no topic filtering)

---

## Complete Workflow Example

### Step 1: Create User
```bash
curl -X POST "http://localhost:8000/users/" \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice"}'
# Response: {"id": 1, "name": "Alice"}
```

### Step 2: Create Chat
```bash
curl -X POST "http://localhost:8000/chats/?user_id=1" \
  -H "Content-Type: application/json" \
  -d '{"name": "AI Research"}'
# Response: {"id": 1, "user_id": 1, "name": "AI Research", ...}
```

### Step 3: Upload Document
```bash
curl -X POST "http://localhost:8000/documents/ingest?user_id=1&chat_id=1" \
  -F "files=@ai_research.pdf"
# Response: {"chunks_count": 42, "status": "embedded and stored", "document_id": 1, "chat_id": 1}
```

### Step 4: Query the Chat
```bash
curl -X POST "http://localhost:8000/chats/query?user_id=1" \
  -H "Content-Type: application/json" \
  -d '{"chat_id": 1, "request": "What are the key findings?"}'
# Response: {"answer": "Based on the document, the key findings are..."}
```

### Step 5: Generate Detailed Summary (Optional)
```bash
curl -X POST "http://localhost:8000/chats/detailed-summarizer?user_id=1" \
  -H "Content-Type: application/json" \
  -d '{"chat_id": 1, "topic_name": "AI Research", "n_results": 5, "max_tokens": 2000}'
# Response: {"summary": "AI Research is...", "topic": "AI Research", "references": [...], "chunks_used": 15}
```

### Step 6: Generate Flashcards (Optional)
```bash
curl -X POST "http://localhost:8000/chats/flashcard?user_id=1&chat_id=1" \
  -H "Content-Type: application/json" \
  -d '{"n_results": 5, "max_tokens": 1000}'
# Response: {"flashcards": [...], "total_topics": 8, "total_flashcards": 32}
```

---

## Architecture Overview

### Data Flow

```
1. PDF Upload
   └─> Extract text → Chunk text → Embed chunks → Store (DB + Vector DB)

2. Query & Chat
   └─> Embed query → Find similar chunks (Top-K) → Pass to LLM with history → Return answer + references

3. Detailed Summarization
   └─> Retrieve topic-specific context → Generate 80/20 summary → Return with references

4. Flashcard Generation
   └─> Retrieve all context → Intelligent topic extraction → Generate flashcards with explanations → Return organized set

5. Isolation
   └─> Each chat scoped by chat_id → User can only access their chats → All operations verify ownership
```

### Technology Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL
- **Vector Store**: ChromaDB (development), pgvector (production-ready)
- **Embeddings**: BAAI/bge-base-en-v1.5 (via HuggingFace)
- **LLM**: meta-llama/Llama-3.1-8B-Instruct (via HuggingFace)
- **ORM**: SQLAlchemy 2.0
- **Migrations**: Alembic

---

## Error Handling

### Common Errors

**404 Not Found - Chat doesn't belong to user:**
```bash
curl "http://localhost:8000/chats/999?user_id=1"
# Response: {"detail": "Chat not found or doesn't belong to you"}
```

**400 Bad Request - Missing required field:**
```bash
curl -X POST "http://localhost:8000/chats/?user_id=1" \
  -H "Content-Type: application/json" \
  -d '{}'
# Response: {"detail": [{"loc": ["body", "name"], "msg": "field required", ...}]}
```

**500 Internal Server Error - PDF processing failed:**
```bash
curl -X POST "http://localhost:8000/documents/ingest?user_id=1&chat_id=1" \
  -F "files=@invalid_file.txt"
# Response: {"detail": "Error processing PDF: ..."}
```

---

## Development

### Clear Database

To start fresh (deletes all users, documents, chats, vectors):

```bash
uv run python3 << 'EOF'
from app.database import Base, engine
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
print("✓ Database cleared")
EOF

rm -rf my_vector_db/
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

- Replace ChromaDB with production vector DB (Qdrant, Milvus, or Pinecone)
- Add authentication/authorization
- Implement rate limiting
- Add comprehensive logging
- Use HTTPS
- Deploy with Docker/Kubernetes
- Set up proper backups for PostgreSQL
- Monitor performance and vector search latency

---

## Troubleshooting

### HuggingFace Token Issues
```bash
# Set your token
export HUGGINGFACE_API_KEY=your_token_here

# Or add to .env file
HUGGINGFACE_API_KEY=your_token_here
```

### PostgreSQL Connection Failed
```bash
# Check PostgreSQL is running
psql -U postgres -c "SELECT 1;"

# Verify connection string in .env
DATABASE_URL=postgresql://user:password@localhost:5432/contextra_ai_db
```

### Out of Memory with ChromaDB
```bash
# Clear ChromaDB
rm -rf my_vector_db/

# Recreate on next run
```

---

## Future Enhancements

- [ ] Support for more file formats (docx, txt, images with OCR)
- [ ] Hybrid search (BM25 + semantic)
- [ ] Document metadata editing
- [ ] Chat history/export
- [ ] Streaming responses
- [ ] Multi-language support
- [ ] Fine-tuned embedding models per domain

---

## License

MIT

## Support

For issues or questions, please open an issue in the repository.
