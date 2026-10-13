import asyncio
from datetime import date

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.dependencies import get_current_user
from app.models.daily_spend import DailySpend
from app.models.user import User
from app.routers.admin import router as admin_router
from app.schemas.user import UserResponse
from app.services import retrieval_service
from app.services import spend_budget_service as budget
from app.settings import settings


@pytest.fixture
def factory(monkeypatch):
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    User.__table__.create(bind=engine)
    DailySpend.__table__.create(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(budget, 'SessionLocal', session_factory)
    monkeypatch.setattr(budget.settings, 'daily_budget_usd', 100.0, raising=False)
    monkeypatch.setattr(budget, '_today', lambda: date(2026, 10, 13))
    return session_factory


def _add_user(factory, **kwargs) -> int:
    db = factory()
    try:
        user = User(name='User', email='user@example.com', password_hash='hash', **kwargs)
        db.add(user)
        db.commit()
        return user.id
    finally:
        db.close()


def _user(factory, user_id) -> User:
    db = factory()
    try:
        return db.get(User, user_id)
    finally:
        db.close()


def test_new_users_default_to_one_dollar_per_month(factory):
    user_id = _add_user(factory)

    assert settings.default_user_budget_usd == 1.0
    assert _user(factory, user_id).monthly_budget_micro_usd == 1_000_000


def test_spend_is_charged_to_user_and_settled_to_real_cost(factory):
    user_id = _add_user(factory)

    with budget.charge_to_user(user_id):
        reserved = budget.reserve(400_000)
        assert _user(factory, user_id).spent_micro_usd == 400_000
        budget.settle(reserved, 12_345)

    user = _user(factory, user_id)
    assert user.spent_micro_usd == 12_345
    assert user.spend_month == '2026-10'


def test_user_is_blocked_once_monthly_budget_is_used(factory):
    user_id = _add_user(factory)

    with budget.charge_to_user(user_id):
        budget.reserve(900_000)
        with pytest.raises(HTTPException) as exc_info:
            budget.reserve(100_001)

    assert exc_info.value.status_code == 429
    assert 'Monthly AI budget reached' in exc_info.value.detail
    assert _user(factory, user_id).spent_micro_usd == 900_000


def test_global_cap_failure_refunds_the_user_reservation(factory, monkeypatch):
    monkeypatch.setattr(budget.settings, 'daily_budget_usd', 0.1, raising=False)
    user_id = _add_user(factory)

    with budget.charge_to_user(user_id):
        with pytest.raises(HTTPException) as exc_info:
            budget.reserve(200_000)

    assert 'Daily AI budget reached' in exc_info.value.detail
    assert _user(factory, user_id).spent_micro_usd == 0


def test_user_budget_resets_in_a_new_month(factory, monkeypatch):
    user_id = _add_user(factory)
    with budget.charge_to_user(user_id):
        budget.reserve(1_000_000)
        with pytest.raises(HTTPException):
            budget.reserve(1)

        monkeypatch.setattr(budget, '_today', lambda: date(2026, 11, 1))
        budget.reserve(1_000_000)

    assert _user(factory, user_id).spend_month == '2026-11'


def test_calls_without_a_user_only_use_the_global_budget(factory):
    user_id = _add_user(factory)

    budget.reserve(500_000)

    assert _user(factory, user_id).spent_micro_usd == 0


def test_user_response_reports_usd_and_ignores_previous_month_spend(factory):
    current_month = date.today().strftime('%Y-%m')
    user_id = _add_user(
        factory, monthly_budget_micro_usd=2_500_000, spent_micro_usd=300_000, spend_month=current_month
    )
    user = _user(factory, user_id)

    response = UserResponse.model_validate(user)
    assert (response.budget_usd, response.spent_usd) == (2.5, 0.3)

    user.spend_month = '2000-01'
    assert UserResponse.model_validate(user).spent_usd == 0


def test_admin_can_update_user_budget(factory, monkeypatch):
    user_id = _add_user(factory, spent_micro_usd=250_000, spend_month='2026-10')
    db = factory()
    try:
        app = FastAPI()
        app.include_router(admin_router)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_user] = lambda: UserResponse(
            id=999, name='Admin', email='admin@example.com', budget_usd=1.0, spent_usd=0.0
        )
        monkeypatch.setattr(settings, 'admin_email', 'admin@example.com', raising=False)
        client = TestClient(app)

        response = client.patch(f'/admin/users/{user_id}/budget', json={'budget_usd': 5.5})

        assert response.status_code == 200
        assert response.json()['budget_usd'] == 5.5
        assert _user(factory, user_id).monthly_budget_micro_usd == 5_500_000

        assert client.patch(f'/admin/users/{user_id}/budget', json={'budget_usd': -1}).status_code == 422
        assert client.patch('/admin/users/12345/budget', json={'budget_usd': 2}).status_code == 404
    finally:
        db.close()


def test_summary_generation_stops_when_user_budget_is_exhausted(factory, monkeypatch):
    user_id = _add_user(factory, monthly_budget_micro_usd=10)

    monkeypatch.setattr(retrieval_service, 'embed_texts', lambda texts: [[0.0]])
    monkeypatch.setattr(
        retrieval_service,
        'query_similar',
        lambda query_embedding, n_results, user_id, chat_id: {
            'documents': [['x' * 400]],
            'metadatas': [[{'filename': 'notes.pdf', 'page': 1, 'document_id': 1}]],
        },
    )

    from app.core import llm

    def fail_if_called(*args, **kwargs):
        pytest.fail('OpenAI should not be called when the user budget is exhausted')

    monkeypatch.setattr(llm, '_create_completion', fail_if_called)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            retrieval_service.generate_detailed_summary(
                db=None,
                topic_name='all',
                user_id=user_id,
                chat_id=1,
                n_results=5,
                max_tokens=50,
            )
        )

    assert exc_info.value.status_code == 429
    assert 'Monthly AI budget reached' in str(exc_info.value.detail)
