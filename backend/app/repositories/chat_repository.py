from sqlalchemy.orm import Session

from app.models.chat import Chat, ChatMessage
from app.models.document import Document
from app.models.embedding import Embedding


def get_chat_by_id(db: Session, chat_id: int) -> Chat | None:
    """Get chat by ID without ownership check."""
    return db.query(Chat).filter(Chat.id == chat_id).first()


def get_chat_for_user(db: Session, chat_id: int, user_id: int) -> Chat | None:
    """Get chat by local_id for a user, verifying ownership by user_id."""
    return db.query(Chat).filter(
        Chat.local_id == chat_id,
        Chat.user_id == user_id
    ).first()


def list_chats_for_user(db: Session, user_id: int) -> list[Chat]:
    """List all chats for a specific user."""
    return db.query(Chat).filter(Chat.user_id == user_id).all()


def create_chat(db: Session, user_id: int, name: str) -> Chat:
    """Create a new chat for a user."""
    # compute next local_id for this user
    last = db.query(Chat).filter(Chat.user_id == user_id).order_by(Chat.local_id.desc()).first()
    next_local = 1 if last is None else (last.local_id + 1)
    chat = Chat(user_id=user_id, local_id=next_local, name=name)
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return chat


def delete_chat(db: Session, chat_id: int, user_id: int) -> bool:
    """Delete a chat, verifying ownership by user_id."""
    chat = db.query(Chat).filter(
        Chat.local_id == chat_id,
        Chat.user_id == user_id
    ).first()
    if chat is None:
        return False
    # remove all messages that reference this chat to avoid FK violations
    db.query(ChatMessage).filter(ChatMessage.chat_id == chat.id).delete()
    # remove embeddings first (FK references documents)
    db.query(Embedding).filter(Embedding.chat_id == chat.id).delete()
    # remove all documents that reference this chat to avoid FK violations
    db.query(Document).filter(Document.chat_id == chat.id).delete()
    db.delete(chat)
    db.commit()
    return True


def update_chat_name(db: Session, chat_id: int, user_id: int, name: str) -> Chat | None:
    """Update chat name, verifying ownership by user_id."""
    chat = db.query(Chat).filter(
        Chat.local_id == chat_id,
        Chat.user_id == user_id
    ).first()
    if chat is None:
        return None
    chat.name = name
    db.commit()
    db.refresh(chat)
    return chat
