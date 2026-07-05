from __future__ import annotations

from math import ceil

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories import user_repository


def estimate_token_cost(*parts: str, max_tokens: int) -> int:
    text = "\n".join(part for part in parts if part)
    estimated_prompt_tokens = max(1, ceil(len(text) / 4)) if text else 1
    return estimated_prompt_tokens + max_tokens


def consume_user_tokens(db: Session, user_id: int, token_cost: int) -> None:
    user = user_repository.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    remaining_tokens = user.token_limit - user.tokens_used
    if token_cost > remaining_tokens:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Token limit exceeded. Remaining tokens: {max(remaining_tokens, 0)}",
        )

    user_repository.add_user_token_usage(db, user_id, token_cost)