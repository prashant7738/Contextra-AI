Key Recommendations
1. Merge into a single FastAPI app
Use app/routers/ with APIRouter to organize endpoints:
- routers/users.py — user CRUD
- routers/documents.py — PDF upload/ingestion
- routers/chat.py — query/chat endpoint
2. Extract service layer
Move logic out of routers into services/:
- services/ingestion_service.py — orchestrates chunk → embed → store
- services/retrieval_service.py — orchestrates embed → query → LLM
- services/user_service.py — user CRUD
3. Extract core logic (pure functions)
- core/chunker.py — sentence-aware text splitting
- core/embedder.py — HF embedding client wrapper
- core/llm.py — HF LLM client wrapper
4. Repository pattern for data access
- repositories/user_repository.py — SQLAlchemy queries
- repositories/vector_repository.py — ChromaDB operations
5. Models & schemas
- models/ — SQLAlchemy ORM models (User, Document, etc.)
- schemas/ — Pydantic request/response models
- database.py — engine, session factory, Base
6. Configuration
Use Pydantic BaseSettings (already in deps) for a clean settings.py instead of raw os.getenv.
7. Make it async
Wrap HF and ChromaDB calls in run_in_executor or use their async clients where available (ChromaDB async client exists, HF has AsyncInferenceClient).
Suggested file structure
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # Unified FastAPI app, include routers
│   ├── database.py          # SQLAlchemy engine & session
│   ├── settings.py          # Pydantic settings from env
│   ├── models/
│   │   ├── __init__.py
│   │   └── user.py          # User ORM model
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── document.py
│   │   └── chat.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── users.py
│   │   ├── documents.py
│   │   └── chat.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── user_service.py
│   │   ├── ingestion_service.py
│   │   └── retrieval_service.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── chunker.py
│   │   ├── embedder.py
│   │   └── llm.py
│   └── repositories/
│       ├── __init__.py
│       ├── user_repository.py
│       └── vector_repository.py
├── pyproject.toml
├── .env
└── alembic/                 # migrations
    ├── alembic.ini
    └── versions/