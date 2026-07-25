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
    TaskStatusResponse,
    FlashcardRequest,
    FlashcardResponse,
    Flashcard,
)
from app.schemas.quiz import (
    QuizRequest,
    QuizGenerateResponse,
    QuizQuestionPublic,
    QuizSubmitRequest,
    QuizSubmitResponse,
    QuizQuestionResult,
    QuizHistoryItem,
)
from app.services.chat_service import (
    create_chat,
    list_user_chats,
    get_chat,
    delete_chat,
)
from app.services.chat_service import update_chat_name
from app.services.retrieval_service import answer_query, generate_detailed_summary, generate_flashcards, generate_quiz
from app.services.quiz_service import grade_quiz_answers
from app.repositories import message_repository, quiz_repository
from app.tasks import start_summary_task
from app.models import SummaryTask

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
async def query_chat(user_id: int, query: QueryRequest, db: Session = Depends(get_db), current_user: UserResponse = Depends(get_current_user)):
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
        answer, references = await answer_query(db, query.request, user_id, chat.id, chat_history=chat_history)
        
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
async def detailed_summarizer(user_id: int, payload: DetailedSummaryRequest, db: Session = Depends(get_db), current_user: UserResponse = Depends(get_current_user)):
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
            initial_answer, _ = await answer_query(
                db=db,
                question=payload.topic_name,
                user_id=user_id,
                chat_id=chat.id,
                chat_history=None,
            )
        
        # Generate detailed summary with optional pre-generated answer as context
        summary, title, sections, references, chunks_used = await generate_detailed_summary(
            db=db,
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
async def generate_flashcard(user_id: int, chat_id: int, payload: Optional[FlashcardRequest] = None, db: Session = Depends(get_db), current_user: UserResponse = Depends(get_current_user)):
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
        
        flashcards, references = await generate_flashcards(
            db=db,
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


@router.post("/summary-task")
async def create_summary_task(
    user_id: int,
    payload: DetailedSummaryRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden: user mismatch")
    chat = get_chat(db, payload.chat_id, user_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found or doesn't belong to you")
    task_id = start_summary_task(db, {
        "user_id": user_id,
        "chat_id": chat.id,
        "topic_name": payload.topic_name,
        "n_results": payload.n_results,
        "max_tokens": payload.max_tokens,
    })
    return {"task_id": task_id}


@router.get("/summary-task/{task_id}", response_model=TaskStatusResponse)
def get_summary_task_status(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    task = db.query(SummaryTask).filter(SummaryTask.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden: task doesn't belong to you")
    return TaskStatusResponse(
        task_id=task.id,
        status=task.status,
        result=DetailedSummaryResponse(**task.result) if task.result else None,
        error=task.error,
    )


@router.post("/quiz", response_model=QuizGenerateResponse)
async def generate_quiz_endpoint(
    user_id: int,
    chat_id: int,
    payload: Optional[QuizRequest] = None,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Generate an MCQ quiz from all uploaded notes in a chat.

    The response never includes correct answers or explanations - those are
    only revealed after the user submits their answers via /quiz/{quiz_id}/submit.

    Args:
        user_id: ID of the user requesting the quiz (query param)
        chat_id: ID of the chat (query param)
        payload: Optional quiz request with num_questions/max_tokens (defaults if not provided)
        db: Database session

    Returns:
        QuizGenerateResponse with quiz_id and questions (no answers)
    """
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden: user mismatch")
    chat = get_chat(db, chat_id, user_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found or doesn't belong to you")

    try:
        num_questions = payload.num_questions if payload else 5
        max_tokens = payload.max_tokens if payload else 1500

        questions, _references = await generate_quiz(
            db=db,
            user_id=user_id,
            chat_id=chat.id,
            num_questions=num_questions,
            max_tokens=max_tokens,
        )

        quiz = quiz_repository.create_quiz(
            db=db,
            user_id=user_id,
            chat_id=chat.id,
            num_questions=len(questions),
            questions=questions,
        )

        return QuizGenerateResponse(
            quiz_id=quiz.id,
            chat_id=quiz.chat_id,
            num_questions=quiz.num_questions,
            questions=[
                QuizQuestionPublic(question=q["question"], options=q["options"])
                for q in questions
            ],
            created_at=quiz.created_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error generating quiz: {str(exc)}")


@router.post("/quiz/{quiz_id}/submit", response_model=QuizSubmitResponse)
def submit_quiz(
    quiz_id: int,
    user_id: int,
    payload: QuizSubmitRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Grade a submitted quiz attempt and reveal correct answers/explanations.

    Args:
        quiz_id: ID of the previously generated quiz
        user_id: ID of the user submitting answers (query param)
        payload: Selected answer index per question
        db: Database session

    Returns:
        QuizSubmitResponse with per-question correctness, explanations, and score
    """
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden: user mismatch")

    quiz = quiz_repository.get_quiz(db, quiz_id, user_id)
    if quiz is None:
        raise HTTPException(status_code=404, detail="Quiz not found or doesn't belong to you")

    questions = quiz.questions or []
    answers = payload.answers
    if len(answers) != len(questions):
        raise HTTPException(
            status_code=422,
            detail=f"Expected {len(questions)} answers, received {len(answers)}",
        )

    results: list[QuizQuestionResult] = []
    score, graded_results = grade_quiz_answers(questions, answers)
    for result in graded_results:
        results.append(
            QuizQuestionResult(
                question=result["question"],
                options=result["options"],
                selected_index=result["selected_index"],
                correct_index=result["correct_index"],
                is_correct=result["is_correct"],
                explanation=result["explanation"],
                references=[Reference(**ref) for ref in result.get("references", [])],
            )
        )

    attempt = quiz_repository.create_quiz_attempt(
        db=db,
        quiz_id=quiz.id,
        user_id=user_id,
        answers=answers,
        score=score,
        total_questions=len(questions),
    )

    return QuizSubmitResponse(
        quiz_id=quiz.id,
        score=score,
        total_questions=len(questions),
        results=results,
        submitted_at=attempt.submitted_at,
    )


@router.get("/quiz-history", response_model=List[QuizHistoryItem])
def get_quiz_history(
    user_id: int,
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    List previously generated quizzes for a chat, with their latest attempt score if any.
    """
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden: user mismatch")
    chat = get_chat(db, chat_id, user_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found or doesn't belong to you")

    quizzes = quiz_repository.list_quiz_history(db, user_id, chat.id)
    history: list[QuizHistoryItem] = []
    for quiz in quizzes:
        latest_attempt = quiz_repository.get_latest_attempt(db, quiz.id, user_id)
        history.append(
            QuizHistoryItem(
                quiz_id=quiz.id,
                num_questions=quiz.num_questions,
                created_at=quiz.created_at,
                last_score=latest_attempt.score if latest_attempt else None,
                last_total_questions=latest_attempt.total_questions if latest_attempt else None,
                last_submitted_at=latest_attempt.submitted_at if latest_attempt else None,
            )
        )
    return history
