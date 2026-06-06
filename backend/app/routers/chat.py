from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.schemas.chat import (
    ChatCreate,
    ChatResponse,
    QueryRequest,
    QueryResponse,
    ChatMessageResponse,
    Reference,
    DetailedSummaryRequest,
    DetailedSummaryResponse,
)
from app.services.chat_service import (
    create_chat,
    list_user_chats,
    get_chat,
    delete_chat,
)
from app.services.retrieval_service import answer_query, generate_detailed_summary
from app.repositories import message_repository

router = APIRouter(prefix="/chats", tags=["chats"])


@router.post("/", response_model=ChatResponse)
def create_new_chat(user_id: int, data: ChatCreate, db: Session = Depends(get_db)):
    """
    Create a new chat for a user.
    
    Args:
        user_id: ID of the user creating the chat
        data: Chat creation data (name)
        db: Database session
    """
    chat = create_chat(db, user_id, data)
    return chat


@router.get("/", response_model=List[ChatResponse])
def list_chats(user_id: int, db: Session = Depends(get_db)):
    """
    List all chats for a user.
    
    Args:
        user_id: ID of the user
        db: Database session
    """
    chats = list_user_chats(db, user_id)
    return chats


@router.get("/{chat_id}", response_model=ChatResponse)
def get_user_chat(chat_id: int, user_id: int, db: Session = Depends(get_db)):
    """
    Get a specific chat (verify ownership).
    
    Args:
        chat_id: ID of the chat
        user_id: ID of the user (for ownership verification)
        db: Database session
    """
    chat = get_chat(db, chat_id, user_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found or doesn't belong to you")
    return chat


@router.delete("/{chat_id}")
def delete_user_chat(chat_id: int, user_id: int, db: Session = Depends(get_db)):
    """
    Delete a chat (verify ownership).
    
    Args:
        chat_id: ID of the chat to delete
        user_id: ID of the user (for ownership verification)
        db: Database session
    """
    deleted = delete_chat(db, chat_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Chat not found or doesn't belong to you")
    return {"ok": True}


@router.post("/query", response_model=QueryResponse)
def query_chat(user_id: int, query: QueryRequest, db: Session = Depends(get_db)):
    """
    Query within a specific chat context.
    
    Args:
        user_id: ID of the user asking the query
        query: Query containing chat_id and request
        db: Database session
    """
    # Verify chat exists and belongs to user
    chat = get_chat(db, query.chat_id, user_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found or doesn't belong to you")
    
    try:
        # Get previous chat history (last 10 messages)
        chat_history = message_repository.get_chat_history(db, query.chat_id, user_id, limit=10)
        
        # Answer query with chat history context
        answer, references = answer_query(query.request, user_id, query.chat_id, chat_history=chat_history)
        
        # Save the message and response to history
        saved_message = message_repository.save_message(db, query.chat_id, user_id, query.request, answer)
        
        # Get updated history to return
        updated_history = message_repository.get_chat_history(db, query.chat_id, user_id, limit=10)
        history_responses = [ChatMessageResponse.model_validate(msg) for msg in updated_history]
        
        return QueryResponse(
            answer=answer,
            references=[Reference(**ref) for ref in references],
            conversation_history=history_responses,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


@router.post("/detailed-summarizer", response_model=DetailedSummaryResponse)
def detailed_summarizer(user_id: int, payload: DetailedSummaryRequest, db: Session = Depends(get_db)):
    """
    Generate an detailed study summary using 80/20 rule from uploaded notes in a chat.

    Args:
        user_id: ID of the user requesting summary
        payload: Summary request with chat_id and topic_name
        db: Database session
    """
    chat = get_chat(db, payload.chat_id, user_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found or doesn't belong to you")

    try:
        summary, references, chunks_used = generate_detailed_summary(
            topic_name=payload.topic_name,
            user_id=user_id,
            chat_id=payload.chat_id,
            n_results=payload.n_results,
            max_tokens=payload.max_tokens,
        )
        return DetailedSummaryResponse(
            summary=summary,
            topic=payload.topic_name,
            references=[Reference(**ref) for ref in references],
            chunks_used=chunks_used,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error generating summary: {str(exc)}")
