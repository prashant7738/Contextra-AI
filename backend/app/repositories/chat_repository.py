from sqlalchemy.orm import Session

from app.models.chat import Chat


def get_chat_by_id(db: Session, chat_id: int) -> Chat | None:
    """Get chat by ID without ownership check."""
    return db.query(Chat).filter(Chat.id == chat_id).first()


def get_chat_for_user(db: Session, chat_id: int, user_id: int) -> Chat | None:
    """Get chat by ID, verifying ownership by user_id."""
    return db.query(Chat).filter(
        Chat.id == chat_id,
        Chat.user_id == user_id
    ).first()


def list_chats_for_user(db: Session, user_id: int) -> list[Chat]:
    """List all chats for a specific user."""
    return db.query(Chat).filter(Chat.user_id == user_id).all()


def create_chat(db: Session, user_id: int, name: str) -> Chat:
    """Create a new chat for a user."""
    chat = Chat(user_id=user_id, name=name)
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return chat


def delete_chat(db: Session, chat_id: int, user_id: int) -> bool:
    """Delete a chat, verifying ownership by user_id."""
    chat = db.query(Chat).filter(
        Chat.id == chat_id,
        Chat.user_id == user_id
    ).first()
    if chat is None:
        return False
    db.delete(chat)
    db.commit()
    return True


def update_chat_name(db: Session, chat_id: int, user_id: int, name: str) -> Chat | None:
    """Update chat name, verifying ownership by user_id."""
    chat = db.query(Chat).filter(
        Chat.id == chat_id,
        Chat.user_id == user_id
    ).first()
    if chat is None:
        return None
    chat.name = name
    db.commit()
    db.refresh(chat)
    return chat
