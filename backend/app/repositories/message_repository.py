from sqlalchemy.orm import Session
from app.models.chat import ChatMessage


def save_message(db: Session, chat_id: int, user_id: int, user_message: str, bot_response: str) -> ChatMessage:
    """Save a user message and bot response to chat history."""
    message = ChatMessage(
        chat_id=chat_id,
        user_id=user_id,
        user_message=user_message,
        bot_response=bot_response
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_chat_history(db: Session, chat_id: int, user_id: int, limit: int = 10) -> list[ChatMessage]:
    """Get recent chat history for a specific chat (limited to last N messages)."""
    messages = db.query(ChatMessage).filter(
        ChatMessage.chat_id == chat_id,
        ChatMessage.user_id == user_id
    ).order_by(ChatMessage.created_at.desc()).limit(limit).all()
    
    # Reverse to get chronological order
    return list(reversed(messages))


def clear_chat_history(db: Session, chat_id: int, user_id: int) -> int:
    """Delete all messages in a chat (verify ownership)."""
    deleted = db.query(ChatMessage).filter(
        ChatMessage.chat_id == chat_id,
        ChatMessage.user_id == user_id
    ).delete()
    db.commit()
    return deleted
