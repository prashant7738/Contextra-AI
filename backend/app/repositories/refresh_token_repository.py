from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, update
from sqlalchemy.orm import Session

from app.models.refresh_token import RefreshToken


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create(db: Session, jti: str, user_id: int, expires_at: datetime) -> RefreshToken:
    row = RefreshToken(id=jti, user_id=user_id, expires_at=expires_at)
    db.add(row)
    return row


def get(db: Session, jti: str) -> RefreshToken | None:
    return db.get(RefreshToken, jti)


def revoke_if_active(db: Session, jti: str, replaced_by: str | None = None) -> bool:
    """Atomically revoke one active token. False if it was already revoked.

    The conditional UPDATE makes concurrent refreshes with the same token safe:
    exactly one of them wins the rotation.
    """
    result = db.execute(
        update(RefreshToken)
        .where(RefreshToken.id == jti, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=_now(), replaced_by=replaced_by)
        .execution_options(synchronize_session=False)
    )
    return result.rowcount == 1


def revoke_all_for_user(db: Session, user_id: int) -> int:
    result = db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=_now())
        .execution_options(synchronize_session=False)
    )
    return result.rowcount


def delete_expired_for_user(db: Session, user_id: int) -> int:
    result = db.execute(
        delete(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.expires_at < _now())
        .execution_options(synchronize_session=False)
    )
    return result.rowcount
