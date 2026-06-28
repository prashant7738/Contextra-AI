import asyncio
import threading
import uuid
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.summary_task import SummaryTask
from app.services.retrieval_service import answer_query, generate_detailed_summary
from app.services.chat_service import get_chat


def start_summary_task(db: Session, params: dict) -> str:
    task_id = str(uuid.uuid4())
    user_id = params["user_id"]
    chat_id = params["chat_id"]
    topic_name = params.get("topic_name") or "all"

    # Create record in DB
    task = SummaryTask(
        id=task_id,
        user_id=user_id,
        chat_id=chat_id,
        topic_name=topic_name,
        status="pending",
    )
    db.add(task)
    db.commit()

    # Start thread
    thread = threading.Thread(
        target=_run_summary_task_sync,
        args=(task_id, params),
        daemon=True,
    )
    thread.start()
    return task_id


def _run_summary_task_sync(task_id: str, params: dict):
    db = SessionLocal()
    try:
        # Update status to processing
        task = db.query(SummaryTask).filter(SummaryTask.id == task_id).first()
        if task:
            task.status = "processing"
            db.commit()

        asyncio.run(_run_summary_task_async(task_id, params, db))
    except Exception as e:
        try:
            task = db.query(SummaryTask).filter(SummaryTask.id == task_id).first()
            if task:
                task.status = "error"
                task.error = str(e)
                task.completed_at = func.now()
                db.commit()
        except Exception as db_err:
            print("Failed to save error status to database:", db_err)
    finally:
        db.close()


async def _run_summary_task_async(task_id: str, params: dict, db: Session):
    user_id = params["user_id"]
    chat_id = params["chat_id"]
    topic_name = params.get("topic_name", "all")
    n_results = params.get("n_results", 5)
    max_tokens = params.get("max_tokens", 700)

    chat = get_chat(db, chat_id, user_id)
    if chat is None:
        raise ValueError("Chat not found or doesn't belong to you")

    normalized_topic = topic_name.strip().lower() if topic_name else ""
    initial_answer = None

    if normalized_topic and normalized_topic != "all":
        initial_answer, _ = await answer_query(
            question=topic_name,
            user_id=user_id,
            chat_id=chat.id,
            chat_history=None,
        )

    summary, title, sections, references, chunks_used = await generate_detailed_summary(
        topic_name=topic_name or "all",
        user_id=user_id,
        chat_id=chat.id,
        n_results=n_results,
        max_tokens=max_tokens,
        pre_generated_answer=initial_answer,
    )

    result = {
        "summary": summary,
        "topic": topic_name or "all",
        "references": [
            {"filename": r.get("filename", ""), "page": r.get("page", 0)}
            for r in references
        ],
        "chunks_used": chunks_used,
        "title": title,
        "sections": [
            {"heading": s.get("heading", ""), "items": s.get("items", [])}
            for s in sections
        ],
    }

    # Update database with result
    task = db.query(SummaryTask).filter(SummaryTask.id == task_id).first()
    if task:
        task.status = "done"
        task.result = result
        task.completed_at = func.now()
        db.commit()
