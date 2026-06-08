from fastapi import HTTPException, status, Depends, Header
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.services import auth_service


def get_token_from_header(authorization: str | None = None) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return parts[1]


def get_current_user(authorization: str | None = Header(None), db: Session = Depends(get_db)):
    token = get_token_from_header(authorization)
    return auth_service.get_current_user(db, token)
