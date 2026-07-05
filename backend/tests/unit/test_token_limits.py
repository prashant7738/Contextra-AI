import asyncio

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.models.user import User
from app.routers.admin import router as admin_router
from app.settings import settings
from app.schemas.user import UserResponse
from app.services import retrieval_service


def _make_sqlite_session():
    engine = create_engine(
        'sqlite://',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    User.__table__.create(bind=engine)
    return SessionLocal()


def test_admin_can_update_user_token_limit(monkeypatch):
    db = _make_sqlite_session()
    try:
        user = User(name='User', email='user@example.com', password_hash='hash', token_limit=25000, tokens_used=100)
        db.add(user)
        db.commit()
        db.refresh(user)

        app = FastAPI()
        app.include_router(admin_router)
        app.dependency_overrides[get_db] = lambda: db

        def override_current_user():
            return UserResponse(id=999, name='Admin', email='admin@example.com', token_limit=50000, tokens_used=0)

        from app.dependencies import get_current_user

        app.dependency_overrides[get_current_user] = override_current_user

        monkeypatch.setattr(settings, 'admin_email', 'admin@example.com', raising=False)
        client = TestClient(app)

        response = client.patch(f'/admin/users/{user.id}/token-limit', json={'token_limit': 12000})

        assert response.status_code == 200
        payload = response.json()
        assert payload['token_limit'] == 12000
        assert payload['tokens_used'] == 100
    finally:
        db.close()


def test_summary_generation_stops_when_user_budget_is_exceeded(monkeypatch):
    db = _make_sqlite_session()
    try:
        user = User(name='User', email='user@example.com', password_hash='hash', token_limit=100, tokens_used=0)
        db.add(user)
        db.commit()
        db.refresh(user)

        monkeypatch.setattr(retrieval_service, 'embed_texts', lambda texts: [[0.0]])
        monkeypatch.setattr(
            retrieval_service,
            'query_similar',
            lambda query_embedding, n_results, user_id, chat_id: {
                'documents': [['x' * 400]],
                'metadatas': [[{'filename': 'notes.pdf', 'page': 1, 'document_id': 1}]],
            },
        )
        monkeypatch.setattr(
            retrieval_service,
            'ask_detailed_summary_llm',
            lambda *args, **kwargs: pytest.fail('LLM should not be called when budget is exceeded'),
        )

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(
                retrieval_service.generate_detailed_summary(
                    db=db,
                    topic_name='all',
                    user_id=user.id,
                    chat_id=1,
                    n_results=5,
                    max_tokens=50,
                )
            )

        assert exc_info.value.status_code == 429
        assert 'Token limit exceeded' in str(exc_info.value.detail)
    finally:
        db.close()