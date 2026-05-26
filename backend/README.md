# Contextra AI Backend

A FastAPI-based backend for a chat-scoped document retrieval system using RAG (Retrieval-Augmented Generation).

## Features

- **User Management**: Create and manage users
- **Chat Sessions**: Each user can have multiple chats for different conversations
- **Document Upload**: Upload PDF documents to specific chats
- **Vector Search**: Semantic search using embeddings (BAAI/bge-base-en-v1.5)
- **Chat-Scoped Context**: AI agent only has access to documents within the current chat
- **LLM Integration**: Uses Llama 3.1 8B for answer generation

## Setup

### Prerequisites
- Python 3.12+
- PostgreSQL
- UV (Python package manager)

### Installation

```bash
# Clone repository
cd "/home/prashant/Coding/Projects/Projects_2/Contextra AI/backend"

# Install dependencies
uv sync

# Create fresh database
uv run python3 << 'EOF'
from app.database import Base, engine
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
print("✓ Database created")
EOF

# Clear vector database (optional)
rm -rf my_vector_db/
```

### Environment Variables

Create a `.env` file in the backend directory:

```
DATABASE_URL=postgresql://user:password@localhost/contextra_ai_db
HUGGINGFACE_API_KEY=your_hf_token_here
CHROMA_PERSIST_DIR=./my_vector_db
CHROMA_COLLECTION_NAME=knowledge-base
```

## Running the Server

```bash
uv run uvicorn app.main:app --reload
```

Server will start at: `http://localhost:8000`

### API Documentation

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## API Endpoints

### 1. Root Endpoint

#### GET `/`
Check if server is running.

```bash
curl http://localhost:8000/
```

**Response:**
```json
{
  "message": "Hello from Second Brain AI",
  "step": 2
}
```

---

## User Management Endpoints

### 2. Create User

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

### 3. List All Users

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

### 4. Get Specific User

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

### 5. Delete User

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

### 6. Create Chat

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

### 7. List User's Chats

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

### 8. Get Specific Chat

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

### 9. Delete Chat

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

### 10. Upload Document to Chat

#### POST `/documents/ingest`
Upload and ingest a PDF document into a specific chat.

```bash
curl -X POST "http://localhost:8000/documents/ingest?user_id=1&chat_id=1" \
  -F "file=@document.pdf"
```

**Parameters:**
- `user_id` (query): ID of the user uploading the document
- `chat_id` (query): ID of the chat to attach the document to
- `file` (form-data): PDF file to upload

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

### 11. Query Within Chat

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
  -F "file=@ai_research.pdf"
# Response: {"chunks_count": 42, "status": "embedded and stored", "document_id": 1, "chat_id": 1}
```

### Step 4: Query the Chat
```bash
curl -X POST "http://localhost:8000/chats/query?user_id=1" \
  -H "Content-Type: application/json" \
  -d '{"chat_id": 1, "request": "What are the key findings?"}'
# Response: {"answer": "Based on the document, the key findings are..."}
```

---

## Architecture Overview

### Data Flow

```
1. PDF Upload
   └─> Extract text → Chunk text → Embed chunks → Store (DB + Vector DB)

2. Query
   └─> Embed query → Find similar chunks (Top-K) → Pass to LLM → Return answer

3. Isolation
   └─> Each chat scoped by chat_id → User can only access their chats
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
  -F "file=@invalid_file.txt"
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

- [ ] User authentication & JWT tokens
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
