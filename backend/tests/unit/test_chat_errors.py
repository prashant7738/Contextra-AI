from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.dependencies import get_current_user
from app.main import app
from app.routers import chat as chat_router
from app.schemas.user import UserResponse


@pytest.fixture
def client(monkeypatch):
    user = UserResponse(id=1, name="u", email="u@x.io", budget_usd=1, spent_usd=0)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: None
    now = datetime(2026, 1, 1)
    monkeypatch.setattr(
        chat_router, "get_chat",
        lambda db, chat_id, user_id: SimpleNamespace(id=9, local_id=chat_id, user_id=user_id, name="c", created_at=now, updated_at=now),
    )
    monkeypatch.setattr(chat_router.message_repository, "get_chat_history", lambda *a, **k: [])
    # No lifespan: TestClient without context manager skips startup DB work.
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_query_without_notes_returns_422(client, monkeypatch):
    async def no_notes(*a, **k):
        raise ValueError("No uploaded notes found in this chat")

    monkeypatch.setattr(chat_router, "answer_query", no_notes)
    resp = client.post("/chats/query?user_id=1", json={"chat_id": 1, "request": "hi"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "No uploaded notes found in this chat"


def test_unexpected_error_returns_generic_500_without_internals(client, monkeypatch):
    async def boom(*a, **k):
        raise RuntimeError("password=hunter2 host=10.0.0.5")

    monkeypatch.setattr(chat_router, "answer_query", boom)
    resp = client.post("/chats/query?user_id=1", json={"chat_id": 1, "request": "hi"})
    assert resp.status_code == 500
    assert "hunter2" not in resp.text
    assert "answering your question" in resp.json()["detail"]


def test_budget_429_passes_through(client, monkeypatch):
    from fastapi import HTTPException

    async def over_budget(*a, **k):
        raise HTTPException(status_code=429, detail="Daily AI budget reached.")

    monkeypatch.setattr(chat_router, "answer_query", over_budget)
    resp = client.post("/chats/query?user_id=1", json={"chat_id": 1, "request": "hi"})
    assert resp.status_code == 429


def test_user_mismatch_forbidden(client):
    resp = client.post("/chats/query?user_id=2", json={"chat_id": 1, "request": "hi"})
    assert resp.status_code == 403
