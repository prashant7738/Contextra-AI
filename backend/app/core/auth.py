"""Password hashing and JWT helpers.

- Passwords: bcrypt directly (passlib is unmaintained). Hashes are standard
  $2b$ strings, so hashes created through passlib keep verifying.
- Tokens: PyJWT (python-jose is unmaintained). Refresh tokens carry a `jti`
  that is tracked server-side so they can be rotated and revoked.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt

from app.settings import settings

# bcrypt only uses the first 72 bytes. passlib (and bcrypt < 4.1) truncated
# silently; bcrypt >= 5 raises instead. Truncate explicitly so long passwords
# keep working and existing hashes still verify.
_BCRYPT_MAX_BYTES = 72


def _password_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(_password_bytes(password), bcrypt.gensalt()).decode("ascii")


def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    """Verify a plain password against its hash. Malformed hashes never match."""
    if not hashed_password:
        return False
    try:
        return bcrypt.checkpw(_password_bytes(plain_password), hashed_password.encode("ascii"))
    except ValueError:
        return False


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a short-lived JWT access token."""
    to_encode = data.copy()
    expire = _now() + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def refresh_token_lifetime() -> timedelta:
    return timedelta(days=settings.refresh_token_expire_days)


def new_token_id() -> str:
    return uuid.uuid4().hex


def create_refresh_token(data: dict, jti: str, expires_at: datetime) -> str:
    """Create a JWT refresh token identified by `jti` (tracked in refresh_tokens)."""
    to_encode = data.copy()
    to_encode.update({"exp": expires_at, "type": "refresh", "jti": jti})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def verify_token(token: str, token_type: str = "access") -> Optional[dict]:
    """Verify a JWT's signature, expiry and type; return its payload or None."""
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
            options={"require": ["exp", "sub"]},
        )
    except jwt.PyJWTError:
        return None
    if payload.get("type") != token_type:
        return None
    return payload
