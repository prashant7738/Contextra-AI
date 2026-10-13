import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.daily_spend import DailySpend
from app.services import spend_budget_service as budget


@pytest.fixture
def session_factory(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    DailySpend.__table__.create(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(budget, "SessionLocal", factory)
    monkeypatch.setattr(budget.settings, "daily_budget_usd", 0.25, raising=False)
    return factory


def _spent(factory):
    db = factory()
    try:
        return sum(row.spent_micro_usd for row in db.query(DailySpend).all())
    finally:
        db.close()


def test_llm_cost_uses_input_cached_and_output_prices():
    # 1M uncached input = $0.10, 1M cached = $0.01, 1M output = $0.50
    assert budget.llm_cost_micro(2_000_000, 1_000_000, 1_000_000) == 100_000 + 10_000 + 500_000


def test_worst_case_assumes_full_output_and_no_caching():
    prompt = "x" * 4000  # ~1000 tokens
    assert budget.llm_worst_case_micro(prompt, 1000) == 100 + 500


def test_reserve_accumulates_and_rejects_over_daily_cap(session_factory):
    budget.reserve(200_000)
    budget.reserve(50_000)  # exactly $0.25, still allowed

    with pytest.raises(HTTPException) as exc_info:
        budget.reserve(1)

    assert exc_info.value.status_code == 429
    assert "Daily AI budget reached" in exc_info.value.detail
    assert _spent(session_factory) == 250_000


def test_rejected_reserve_does_not_change_spend(session_factory):
    budget.reserve(240_000)

    with pytest.raises(HTTPException):
        budget.reserve(20_000)

    assert _spent(session_factory) == 240_000


def test_settle_refunds_unused_reservation_and_charges_overage(session_factory):
    reserved = budget.reserve(100_000)
    budget.settle(reserved, 30_000)
    assert _spent(session_factory) == 30_000

    budget.settle(30_000, 35_000)
    assert _spent(session_factory) == 35_000


def test_new_utc_day_starts_with_a_fresh_budget(session_factory, monkeypatch):
    from datetime import date

    monkeypatch.setattr(budget, "_today", lambda: date(2026, 10, 13))
    budget.reserve(250_000)
    with pytest.raises(HTTPException):
        budget.reserve(1)

    monkeypatch.setattr(budget, "_today", lambda: date(2026, 10, 14))
    budget.reserve(250_000)

    assert _spent(session_factory) == 500_000


def test_get_today_spend_reports_remaining(session_factory):
    budget.reserve(100_000)

    info = budget.get_today_spend()

    assert info["spent_usd"] == 0.1
    assert info["budget_usd"] == 0.25
    assert info["remaining_usd"] == 0.15
