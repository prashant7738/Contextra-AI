from sqlalchemy.orm import Session

from app.repositories import chat_repository
from app.schemas.chat import ChatCreate, ChatResponse


def list_user_chats(db: Session, user_id: int) -> list[ChatResponse]:
    """List all chats for a user."""
    chats = chat_repository.list_chats_for_user(db, user_id)
    return [ChatResponse.model_validate(c) for c in chats]


def get_chat(db: Session, chat_id: int, user_id: int) -> ChatResponse | None:
    """Get a specific chat, verifying ownership."""
    chat = chat_repository.get_chat_for_user(db, chat_id, user_id)
    if chat is None:
        return None
    return ChatResponse.model_validate(chat)


def create_chat(db: Session, user_id: int, data: ChatCreate) -> ChatResponse:
    """Create a new chat for a user."""
    chat = chat_repository.create_chat(db, user_id, name=data.name)
    return ChatResponse.model_validate(chat)


def delete_chat(db: Session, chat_id: int, user_id: int) -> bool:
    """Delete a chat, verifying ownership."""
    return chat_repository.delete_chat(db, chat_id, user_id)


def update_chat_name(db: Session, chat_id: int, user_id: int, name: str) -> ChatResponse | None:
    """Update chat name, verifying ownership."""
    chat = chat_repository.update_chat_name(db, chat_id, user_id, name)
    if chat is None:
        return None
    return ChatResponse.model_validate(chat)
