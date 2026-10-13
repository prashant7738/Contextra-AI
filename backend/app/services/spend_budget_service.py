"""Global daily USD budget for OpenAI calls.

Every OpenAI call first reserves its worst-case cost with a single conditional
UPDATE, so concurrent requests can't jointly exceed the cap, then settles the
reservation to the real cost reported by the API.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from math import ceil

from fastapi import HTTPException, status
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app.models.daily_spend import DailySpend
from app.settings import settings

MICRO = 1_000_000


def _today() -> date:
    return datetime.now(timezone.utc).date()


def usd_to_micro(usd: float) -> int:
    return ceil(usd * MICRO)


def estimate_tokens(*parts: str) -> int:
    text = "\n".join(part for part in parts if part)
    return max(1, ceil(len(text) / 4))


def _tokens_cost_micro(tokens: float, price_per_million_usd: float) -> int:
    # price (USD / 1M tokens) * tokens == micro-USD
    return ceil(tokens * price_per_million_usd)


def llm_cost_micro(prompt_tokens: int, cached_tokens: int, completion_tokens: int) -> int:
    uncached = max(prompt_tokens - cached_tokens, 0)
    return (
        _tokens_cost_micro(uncached, settings.llm_input_price_per_m)
        + _tokens_cost_micro(cached_tokens, settings.llm_cached_input_price_per_m)
        + _tokens_cost_micro(completion_tokens, settings.llm_output_price_per_m)
    )


def llm_worst_case_micro(prompt: str, max_tokens: int) -> int:
    """Upper bound: whole prompt uncached, and the full output allowance used."""
    return llm_cost_micro(estimate_tokens(prompt), 0, max_tokens)


def embedding_cost_micro(tokens: int) -> int:
    return _tokens_cost_micro(tokens, settings.embedding_price_per_m)


def _ensure_row(db, day: date) -> None:
    if db.get(DailySpend, day) is not None:
        return
    try:
        db.add(DailySpend(day=day, spent_micro_usd=0))
        db.commit()
    except IntegrityError:
        # Another request created today's row first.
        db.rollback()


def reserve(micro_usd: int) -> int:
    """Atomically add micro_usd to today's spend, or raise 429 if it would pass the cap."""
    micro_usd = max(int(micro_usd), 0)
    cap = usd_to_micro(settings.daily_budget_usd)
    day = _today()
    db = SessionLocal()
    try:
        _ensure_row(db, day)
        result = db.execute(
            update(DailySpend)
            .where(DailySpend.day == day, DailySpend.spent_micro_usd + micro_usd <= cap)
            .values(spent_micro_usd=DailySpend.spent_micro_usd + micro_usd)
        )
        db.commit()
        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Daily AI budget reached. It resets at 00:00 UTC.",
            )
        return micro_usd
    finally:
        db.close()


def settle(reserved_micro_usd: int, actual_micro_usd: int) -> None:
    """Replace a reservation with the real cost (refunds the difference, or charges overage)."""
    delta = int(actual_micro_usd) - int(reserved_micro_usd)
    if delta == 0:
        return
    day = _today()
    db = SessionLocal()
    try:
        _ensure_row(db, day)
        db.execute(
            update(DailySpend)
            .where(DailySpend.day == day)
            .values(spent_micro_usd=DailySpend.spent_micro_usd + delta)
        )
        db.commit()
    finally:
        db.close()


def get_today_spend() -> dict:
    cap = usd_to_micro(settings.daily_budget_usd)
    day = _today()
    db = SessionLocal()
    try:
        row = db.get(DailySpend, day)
        spent = row.spent_micro_usd if row else 0
    finally:
        db.close()
    return {
        "day": day.isoformat(),
        "spent_usd": round(spent / MICRO, 6),
        "budget_usd": settings.daily_budget_usd,
        "remaining_usd": round(max(cap - spent, 0) / MICRO, 6),
    }
