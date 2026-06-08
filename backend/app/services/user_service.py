from sqlalchemy.orm import Session

from app.repositories import user_repository
from app.schemas.user import UserCreate, UserResponse


def list_users(db: Session, skip: int = 0, limit: int = 100) -> list[UserResponse]:
    users = user_repository.get_users(db, skip=skip, limit=limit)
    return [UserResponse.model_validate(u) for u in users]


def get_user(db: Session, user_id: int) -> UserResponse | None:
    user = user_repository.get_user_by_id(db, user_id)
    if user is None:
        return None
    return UserResponse.model_validate(user)


def delete_user(db: Session, user_id: int) -> bool:
    return user_repository.delete_user(db, user_id)
