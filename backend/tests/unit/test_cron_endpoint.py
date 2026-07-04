from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.cron import router as cron_router
from app.settings import settings


def _make_client() -> TestClient:
    app = FastAPI()
    app.include_router(cron_router)
    return TestClient(app)


def test_cron_endpoint_accepts_valid_secret(monkeypatch):
    monkeypatch.setattr(settings, "cron_secret", "test-secret", raising=False)
    client = _make_client()

    response = client.post("/cron/run", headers={"X-Cron-Secret": "test-secret"})

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["job"] == "maintenance"


def test_cron_endpoint_rejects_invalid_secret(monkeypatch):
    monkeypatch.setattr(settings, "cron_secret", "test-secret", raising=False)
    client = _make_client()

    response = client.post("/cron/run", headers={"X-Cron-Secret": "wrong-secret"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid cron secret"