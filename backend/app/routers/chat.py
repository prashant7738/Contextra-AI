from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.dependencies import get_current_user
from app.schemas.user import UserResponse
from app.schemas.chat import (
    ChatCreate,
    ChatResponse,
    QueryRequest,
    QueryResponse,
    ChatMessageResponse,
    Reference,
    DetailedSummaryRequest,
    DetailedSummaryResponse,
    FlashcardRequest,
    FlashcardResponse,
    Flashcard,
)
from app.services.chat_service import (
    create_chat,
    list_user_chats,
    get_chat,
    delete_chat,
)
from app.services.chat_service import update_chat_name
from app.services.retrieval_service import answer_query, generate_detailed_summary, generate_flashcards
from app.repositories import message_repository

router = APIRouter(prefix="/chats", tags=["chats"])


@router.get("/{chat_id}/messages", response_model=List[ChatMessageResponse])
def get_chat_messages(chat_id: int, user_id: int, limit: int = Query(default=50, ge=1, le=200), db: Session = Depends(get_db), current_user: UserResponse = Depends(get_current_user)):
    """
    Return the recent message history for a chat.
    """
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden: user mismatch")

    chat = get_chat(db, chat_id, user_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found or doesn't belong to you")

    messages = message_repository.get_chat_history(db, chat.id, user_id, limit=limit)
    return [ChatMessageResponse.model_validate(message) for message in messages]


@router.post("/", response_model=ChatResponse)
def create_new_chat(user_id: int, data: ChatCreate, db: Session = Depends(get_db), current_user: UserResponse = Depends(get_current_user)):
    """
    Create a new chat for a user.
    
    Args:
        user_id: ID of the user creating the chat
        data: Chat creation data (name)
        db: Database session
    """
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden: user mismatch")
    chat = create_chat(db, user_id, data)
    return chat


@router.get("/", response_model=List[ChatResponse])
def list_chats(user_id: int, db: Session = Depends(get_db), current_user: UserResponse = Depends(get_current_user)):
    """
    List all chats for a user.
    
    Args:
        user_id: ID of the user
        db: Database session
    """
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden: user mismatch")
    chats = list_user_chats(db, user_id)
    return chats


@router.get("/{chat_id}", response_model=ChatResponse)
def get_user_chat(chat_id: int, user_id: int, db: Session = Depends(get_db), current_user: UserResponse = Depends(get_current_user)):
    """
    Get a specific chat (verify ownership).
    
    Args:
        chat_id: ID of the chat
        user_id: ID of the user (for ownership verification)
        db: Database session
    """
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden: user mismatch")
    chat = get_chat(db, chat_id, user_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found or doesn't belong to you")
    return chat


@router.delete("/{chat_id}")
def delete_user_chat(chat_id: int, user_id: int, db: Session = Depends(get_db), current_user: UserResponse = Depends(get_current_user)):
    """
    Delete a chat (verify ownership).
    
    Args:
        chat_id: ID of the chat to delete
        user_id: ID of the user (for ownership verification)
        db: Database session
    """
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden: user mismatch")
    # Log delete attempt for debugging (shows local_id and user)
    print(f"Attempting delete: chat_id={chat_id}, user_id={user_id}, current_user.id={current_user.id}")
    # Verify chat exists before deletion to provide clearer logs
    chat = get_chat(db, chat_id, user_id)
    print("Found chat for deletion:", bool(chat))
    deleted = delete_chat(db, chat_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Chat not found or doesn't belong to you")
    return {"ok": True}


@router.patch("/{chat_id}", response_model=ChatResponse)
def patch_user_chat(chat_id: int, user_id: int, data: ChatCreate, db: Session = Depends(get_db), current_user: UserResponse = Depends(get_current_user)):
    """
    Update a chat's name (verify ownership).
    """
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden: user mismatch")
    updated = update_chat_name(db, chat_id, user_id, data.name)
    if updated is None:
        raise HTTPException(status_code=404, detail="Chat not found or doesn't belong to you")
    return updated


@router.post("/query", response_model=QueryResponse)
def query_chat(user_id: int, query: QueryRequest, db: Session = Depends(get_db), current_user: UserResponse = Depends(get_current_user)):
    """
    Query within a specific chat context.
    
    Args:
        user_id: ID of the user asking the query
        query: Query containing chat_id and request
        db: Database session
    """
    # Verify chat exists and belongs to user
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden: user mismatch")
    chat = get_chat(db, query.chat_id, user_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found or doesn't belong to you")
    
    try:
        # Get previous chat history (last 10 messages)
        chat_history = message_repository.get_chat_history(db, chat.id, user_id, limit=10)
        
        # Answer query with chat history context
        answer, references = answer_query(query.request, user_id, chat.id, chat_history=chat_history)
        
        # Save the message and response to history
        saved_message = message_repository.save_message(db, chat.id, user_id, query.request, answer)
        
        # Get updated history to return
        updated_history = message_repository.get_chat_history(db, chat.id, user_id, limit=10)
        history_responses = [ChatMessageResponse.model_validate(msg) for msg in updated_history]
        
        return QueryResponse(
            answer=answer,
            references=[Reference(**ref) for ref in references],
            conversation_history=history_responses,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


@router.post("/detailed-summarizer", response_model=DetailedSummaryResponse)
def detailed_summarizer(user_id: int, payload: DetailedSummaryRequest, db: Session = Depends(get_db), current_user: UserResponse = Depends(get_current_user)):
    """
    Generate an detailed study summary using 80/20 rule from uploaded notes in a chat.
    
    Flow:
    - If topic_name is "all" or empty: directly generate summary with full context
    - If topic_name is specific: 
      1. First call answer_query with topic_name to get LLM-enriched context
      2. Then generate detailed summary with that context, allowing LLM to expand further

    Args:
        user_id: ID of the user requesting summary
        payload: Summary request with chat_id and topic_name
        db: Database session
    """
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden: user mismatch")
    chat = get_chat(db, payload.chat_id, user_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found or doesn't belong to you")

    try:
        normalized_topic = payload.topic_name.strip().lower() if payload.topic_name else ""
        initial_answer = None
        
        # Only call answer_query for specific topics, not for "all"
        if normalized_topic and normalized_topic != "all":
            initial_answer, _ = answer_query(
                question=payload.topic_name,
                user_id=user_id,
                chat_id=chat.id,
                chat_history=None
            )
        
        # Generate detailed summary with optional pre-generated answer as context
        summary, title, sections, references, chunks_used = generate_detailed_summary(
            topic_name=payload.topic_name or "all",
            user_id=user_id,
            chat_id=chat.id,
            n_results=payload.n_results,
            max_tokens=payload.max_tokens,
            pre_generated_answer=initial_answer,
        )
        return DetailedSummaryResponse(
            summary=summary,
            topic=payload.topic_name or "all",
            references=[Reference(**ref) for ref in references],
            chunks_used=chunks_used,
            title=title,
            sections=sections,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error generating summary: {str(exc)}")


@router.post("/flashcard", response_model=FlashcardResponse)
def generate_flashcard(user_id: int, chat_id: int, payload: Optional[FlashcardRequest] = None, db: Session = Depends(get_db), current_user: UserResponse = Depends(get_current_user)):
    """
    Generate flashcards from all uploaded notes in a chat.
    
    Flashcard generation:
    - Always uses ALL context (no topic filtering)
    - Creates intelligent distribution of flashcards:
      * Important/large topics: 8-12 flashcards
      * Medium topics: 4-7 flashcards
      * Small/basic topics: 2-3 flashcards
    - Each flashcard has: topic, summary (one line), detailed explanation
    - Includes references to source documents

    Args:
        user_id: ID of the user requesting flashcards (query param)
        chat_id: ID of the chat (query param)
        payload: Optional flashcard request with n_results/max_tokens (defaults if not provided)
        db: Database session
    
    Returns:
        FlashcardResponse with list of flashcards and metadata
    """
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden: user mismatch")
    chat = get_chat(db, chat_id, user_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found or doesn't belong to you")

    try:
        # Use defaults if payload not provided
        n_results = payload.n_results if payload else 5
        max_tokens = payload.max_tokens if payload else 1000
        
        flashcards, references = generate_flashcards(
            user_id=user_id,
            chat_id=chat.id,
            n_results=n_results,
            max_tokens=max_tokens,
        )
        
        # Convert to Flashcard models
        flashcard_models = [
            Flashcard(
                topic=fc.get("topic", "Unknown"),
                summary=fc.get("summary", ""),
                explanation=fc.get("explanation", ""),
                references=[Reference(**ref) for ref in fc.get("references", [])],
            )
            for fc in flashcards
        ]
        
        # Count unique topics
        unique_topics = len(set(fc.topic for fc in flashcard_models))
        
        return FlashcardResponse(
            flashcards=flashcard_models,
            total_topics=unique_topics,
            total_flashcards=len(flashcard_models),
        )
    
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error generating flashcards: {str(exc)}")
