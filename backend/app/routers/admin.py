from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.dependencies import get_current_user
from app.settings import settings
from app.repositories import chat_repository
from app.models.user import User
from app.schemas.user import UserResponse
from app.schemas.chat import ChatResponse, ChatMessageResponse

router = APIRouter(prefix="/admin", tags=["admin"])


def _ensure_admin(current_user: UserResponse):
    if not settings.admin_email:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Admin not configured")
    if current_user.email != settings.admin_email:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")


@router.get("/users", response_model=List[UserResponse])
def admin_list_users(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_admin(current_user)
    users = db.query(User).order_by(User.id.asc()).all()
    return [UserResponse.model_validate(u) for u in users]


@router.get("/users/{user_id}/chats", response_model=List[ChatResponse])
def admin_list_user_chats(
    user_id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_admin(current_user)
    chats = chat_repository.list_chats_for_user(db, user_id)
    result = []
    for c in chats:
        result.append(ChatResponse.model_validate(c))
    return result


@router.get("/chats/{chat_id}/messages", response_model=List[ChatMessageResponse])
def admin_get_chat_messages(
    chat_id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_admin(current_user)
    # Return messages without enforcing ownership
    from app.models.chat import ChatMessage
    messages = db.query(ChatMessage).filter(ChatMessage.chat_id == chat_id).order_by(ChatMessage.created_at.asc()).all()
    return [ChatMessageResponse.model_validate(m) for m in messages]
