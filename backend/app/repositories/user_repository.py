from math import ceil

from sqlalchemy.orm import Session

from app.models.user import User
from app.core.auth import hash_password
from app.settings import settings

MICRO = 1_000_000


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
        monthly_budget_micro_usd=ceil(settings.default_user_budget_usd * MICRO),
        spent_micro_usd=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user_budget(db: Session, user_id: int, budget_usd: float) -> User | None:
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        return None
    user.monthly_budget_micro_usd = ceil(budget_usd * MICRO)
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: int) -> bool:
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        return False
    db.delete(user)
    db.commit()
    return True
