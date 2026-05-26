from sqlalchemy.orm import Session
from app.models.document import Document
from app.repositories import user_repository, chat_repository


def create_document(db: Session, user_id: int, chat_id: int, filename: str, content: str = None) -> Document:
    """
    Create a new document record in the database.
    
    Args:
        db: Database session
        user_id: ID of the user uploading the document
        chat_id: ID of the chat this document belongs to
        filename: Name of the document file
        content: Full text content of the document
    
    Returns:
        The created Document object (with its ID).
    
    Raises:
        ValueError: If user or chat not found, or chat doesn't belong to user
    """
    # Verify user exists
    user = user_repository.get_user_by_id(db, user_id)
    if user is None:
        raise ValueError(f"User with ID {user_id} not found")
    
    # Verify chat exists and belongs to the user
    chat = chat_repository.get_chat_for_user(db, chat_id, user_id)
    if chat is None:
        raise ValueError(f"Chat with ID {chat_id} not found or doesn't belong to user {user_id}")
    
    # Create document record
    doc = Document(
        user_id=user_id,
        chat_id=chat_id,
        filename=filename,
        content=content or ""
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def get_user_documents(db: Session, user_id: int) -> list[Document]:
    """Get all documents for a user."""
    return db.query(Document).filter(Document.user_id == user_id).all()


def delete_document(db: Session, document_id: int, user_id: int) -> bool:
    """Delete a document (only if it belongs to the user)."""
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == user_id
    ).first()
    
    if doc is None:
        return False
    
    db.delete(doc)
    db.commit()
    return True
