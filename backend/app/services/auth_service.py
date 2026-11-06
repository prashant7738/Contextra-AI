import logging
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import (
    create_access_token,
    create_refresh_token,
    new_token_id,
    refresh_token_lifetime,
    verify_password,
    verify_token,
)
from app.repositories import refresh_token_repository, user_repository
from app.schemas.auth import TokenResponse, UserLogin
from app.schemas.user import UserCreate, UserResponse

logger = logging.getLogger(__name__)

# Two tabs (or a retry) may refresh with the same token at nearly the same
# time. Reuse within this window after rotation is answered with 401 but is not
# treated as theft; later reuse revokes every session of the user.
REUSE_GRACE = timedelta(seconds=30)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def register_user(db: Session, user_data: UserCreate) -> TokenResponse:
    """Register a new user and return access and refresh tokens."""
    if user_repository.get_user_by_email(db, user_data.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = user_repository.create_user(
        db,
        name=user_data.name,
        email=user_data.email,
        password=user_data.password,
    )
    return _issue_tokens(db, user.id)


def login_user(db: Session, login_data: UserLogin) -> TokenResponse:
    """Authenticate user and return access and refresh tokens."""
    user = user_repository.get_user_by_email(db, login_data.email)
    if not user or not verify_password(login_data.password, user.password_hash):
        raise _unauthorized("Invalid email or password")

    refresh_token_repository.delete_expired_for_user(db, user.id)
    return _issue_tokens(db, user.id)


def refresh_access_token(db: Session, refresh_token: str) -> TokenResponse:
    """Rotate a refresh token: revoke it and issue a new access/refresh pair."""
    payload = verify_token(refresh_token, token_type="refresh")
    jti = payload.get("jti") if payload else None
    if not payload or not jti:
        raise _unauthorized("Invalid refresh token")

    user_id = int(payload["sub"])
    row = refresh_token_repository.get(db, jti)
    if row is None or row.user_id != user_id:
        raise _unauthorized("Invalid refresh token")

    new_jti = new_token_id()
    if not refresh_token_repository.revoke_if_active(db, jti, replaced_by=new_jti):
        db.rollback()
        _handle_reuse(db, row)
        raise _unauthorized("Refresh token has already been used")

    if user_repository.get_user_by_id(db, user_id) is None:
        db.rollback()
        raise _unauthorized("User not found")

    return _issue_tokens(db, user_id, jti=new_jti)


def _handle_reuse(db: Session, row) -> None:
    db.refresh(row)
    revoked_at = row.revoked_at
    if revoked_at is not None and revoked_at.tzinfo is None:
        revoked_at = revoked_at.replace(tzinfo=timezone.utc)
    if revoked_at is not None and datetime.now(timezone.utc) - revoked_at <= REUSE_GRACE and row.replaced_by:
        return  # concurrent refresh, not theft
    revoked = refresh_token_repository.revoke_all_for_user(db, row.user_id)
    db.commit()
    logger.warning("Refresh token reuse for user %s: revoked %d active sessions", row.user_id, revoked)


def logout(db: Session, refresh_token: str) -> None:
    """Revoke the given refresh token. Idempotent; invalid tokens are ignored."""
    payload = verify_token(refresh_token, token_type="refresh")
    jti = payload.get("jti") if payload else None
    if not jti:
        return
    row = refresh_token_repository.get(db, jti)
    if row is None or row.user_id != int(payload["sub"]):
        return
    refresh_token_repository.revoke_if_active(db, jti)
    db.commit()


def get_current_user(db: Session, token: str) -> UserResponse:
    """Get current user from access token."""
    payload = verify_token(token, token_type="access")
    if not payload:
        raise _unauthorized("Invalid access token")

    user = user_repository.get_user_by_id(db, int(payload["sub"]))
    if not user:
        raise _unauthorized("User not found")
    return UserResponse.model_validate(user)


def _issue_tokens(db: Session, user_id: int, jti: str | None = None) -> TokenResponse:
    """Issue an access token and a tracked refresh token, committing the row."""
    jti = jti or new_token_id()
    expires_at = datetime.now(timezone.utc) + refresh_token_lifetime()
    refresh_token_repository.create(db, jti=jti, user_id=user_id, expires_at=expires_at)
    db.commit()
    return TokenResponse(
        access_token=create_access_token({"sub": str(user_id)}),
        refresh_token=create_refresh_token({"sub": str(user_id)}, jti=jti, expires_at=expires_at),
        token_type="bearer",
    )
