"""Refresh-token rotation, reuse detection and logout against a real database."""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core import rate_limit
from app.database import engine
from app.main import app
from app.services import auth_service


def _db_available() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1 FROM refresh_tokens LIMIT 0"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_available(), reason="needs a migrated PostgreSQL database")


@pytest.fixture
def client():
    rate_limit.reset_all_limiters()
    yield TestClient(app)
    rate_limit.reset_all_limiters()


def _register(client):
    email = f"rt-{uuid.uuid4().hex[:10]}@example.com"
    resp = client.post("/auth/register", json={"name": "R", "email": email, "password": "password123"})
    assert resp.status_code == 200, resp.text
    return email, resp.json()


def test_refresh_rotates_and_old_token_is_rejected(client):
    _, tokens = _register(client)
    first = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert first.status_code == 200
    rotated = first.json()
    assert rotated["refresh_token"] != tokens["refresh_token"]

    again = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert again.status_code == 401
    # Within the grace window the new token keeps working (concurrent tabs).
    assert client.post("/auth/refresh", json={"refresh_token": rotated["refresh_token"]}).status_code == 200


def test_reuse_after_grace_revokes_all_sessions(client, monkeypatch):
    from datetime import timedelta

    _, tokens = _register(client)
    rotated = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).json()
    monkeypatch.setattr(auth_service, "REUSE_GRACE", timedelta(seconds=-1))

    stolen = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert stolen.status_code == 401
    # The legitimate (rotated) session was revoked as well.
    assert client.post("/auth/refresh", json={"refresh_token": rotated["refresh_token"]}).status_code == 401


def test_logout_revokes_refresh_token_and_is_idempotent(client):
    email, tokens = _register(client)
    assert client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]}).status_code == 204
    assert client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]}).status_code == 204
    assert client.post("/auth/logout", json={"refresh_token": "garbage"}).status_code == 204
    assert client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401

    # Other sessions are unaffected.
    other = client.post("/auth/login", json={"email": email, "password": "password123"}).json()
    assert client.post("/auth/refresh", json={"refresh_token": other["refresh_token"]}).status_code == 200


def test_legacy_refresh_token_without_jti_is_rejected(client):
    import jwt
    from datetime import datetime, timedelta, timezone
    from app.settings import settings

    legacy = jwt.encode(
        {"sub": "1", "type": "refresh", "exp": datetime.now(timezone.utc) + timedelta(days=1)},
        settings.secret_key, algorithm=settings.algorithm,
    )
    assert client.post("/auth/refresh", json={"refresh_token": legacy}).status_code == 401
