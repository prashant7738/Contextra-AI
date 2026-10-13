"""USD budgets for OpenAI calls: a global daily cap and a per-user monthly cap.

Every OpenAI call first reserves its worst-case cost with a single conditional
UPDATE, so concurrent requests can't jointly exceed a cap, then settles the
reservation to the real cost reported by the API. The per-user budget applies
when a user is set with `charge_to_user`; otherwise only the global cap applies.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from datetime import date, datetime, timezone
from math import ceil

from fastapi import HTTPException, status
from sqlalchemy import or_, update
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app.models.daily_spend import DailySpend
from app.models.user import User
from app.settings import settings

MICRO = 1_000_000


_current_user_id: ContextVar[int | None] = ContextVar("spend_user_id", default=None)


@contextmanager
def charge_to_user(user_id: int | None):
    """Attribute OpenAI spend made inside this block to a user's monthly budget."""
    token = _current_user_id.set(user_id)
    try:
        yield
    finally:
        _current_user_id.reset(token)


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _month() -> str:
    return _today().strftime("%Y-%m")


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


def _reserve_global(micro_usd: int) -> None:
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
    finally:
        db.close()


def _reserve_user(user_id: int, micro_usd: int) -> None:
    month = _month()
    db = SessionLocal()
    try:
        # A new UTC month starts every user at $0 spent.
        db.execute(
            update(User)
            .where(User.id == user_id, or_(User.spend_month.is_(None), User.spend_month != month))
            .values(spent_micro_usd=0, spend_month=month)
        )
        result = db.execute(
            update(User)
            .where(User.id == user_id, User.spent_micro_usd + micro_usd <= User.monthly_budget_micro_usd)
            .values(spent_micro_usd=User.spent_micro_usd + micro_usd)
        )
        db.commit()
        if result.rowcount == 0:
            user = db.get(User, user_id)
            if user is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Monthly AI budget reached (${user.spent_micro_usd / MICRO:.2f} of "
                    f"${user.monthly_budget_micro_usd / MICRO:.2f} used). It resets on the 1st (UTC)."
                ),
            )
    finally:
        db.close()


def _adjust_user(user_id: int, delta: int) -> None:
    db = SessionLocal()
    try:
        db.execute(
            update(User)
            .where(User.id == user_id, User.spend_month == _month())
            .values(spent_micro_usd=User.spent_micro_usd + delta)
        )
        db.commit()
    finally:
        db.close()


def reserve(micro_usd: int) -> int:
    """Atomically add micro_usd to the user's month and today's global spend, or raise 429."""
    micro_usd = max(int(micro_usd), 0)
    user_id = _current_user_id.get()
    if user_id is not None:
        _reserve_user(user_id, micro_usd)
    try:
        _reserve_global(micro_usd)
    except Exception:
        if user_id is not None:
            _adjust_user(user_id, -micro_usd)
        raise
    return micro_usd


def settle(reserved_micro_usd: int, actual_micro_usd: int) -> None:
    """Replace a reservation with the real cost (refunds the difference, or charges overage)."""
    delta = int(actual_micro_usd) - int(reserved_micro_usd)
    if delta == 0:
        return
    user_id = _current_user_id.get()
    if user_id is not None:
        _adjust_user(user_id, delta)
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
