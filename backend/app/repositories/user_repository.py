from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models.user import User
from app.core.auth import hash_password
from app.settings import settings


def get_users(db: Session, skip: int = 0, limit: int = 100) -> list[User]:
    return db.query(User).offset(skip).limit(limit).all()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, name: str, email: str, password: str) -> User:
    password_hash = hash_password(password)
    user = User(
        name=name,
        email=email,
        password_hash=password_hash,
        token_limit=settings.default_user_token_limit,
        tokens_used=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user_token_limit(db: Session, user_id: int, token_limit: int) -> User | None:
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        return None
    user.token_limit = token_limit
    db.commit()
    db.refresh(user)
    return user


def add_user_token_usage(db: Session, user_id: int, token_usage: int) -> User | None:
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        return None
    user.tokens_used += token_usage
    db.commit()
    db.refresh(user)
    return user


def try_consume_user_tokens(db: Session, user_id: int, token_cost: int) -> User | None:
    """Atomically deduct token_cost from a user's remaining budget.

    Uses a single conditional UPDATE (checked and applied by the database in
    one statement) instead of a separate read-then-write, so concurrent
    requests from the same user can't both pass a stale "remaining tokens"
    check and jointly exceed token_limit.

    Returns the updated User on success, or None if the user doesn't exist or
    doesn't have enough remaining budget.
    """
    result = db.execute(
        update(User)
        .where(
            User.id == user_id,
            (User.token_limit - User.tokens_used) >= token_cost,
        )
        .values(tokens_used=User.tokens_used + token_cost)
    )
    db.commit()
    if result.rowcount == 0:
        return None
    return get_user_by_id(db, user_id)


def delete_user(db: Session, user_id: int) -> bool:
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        return False
    db.delete(user)
    db.commit()
    return True
