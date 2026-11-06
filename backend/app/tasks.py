"""Summary generation jobs.

`start_summary_task` only records the job; a job-queue worker
(app/core/job_queue.py) claims it and calls `run_summary_task`. Everything the
worker needs is stored in the row, so a job survives a process restart.
"""
import asyncio
import logging
import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core import job_queue
from app.database import SessionLocal
from app.models.summary_task import SummaryTask
from app.repositories.chat_repository import get_chat_by_id
from app.services.background_ingestion import user_facing_error
from app.services.retrieval_service import answer_query, generate_detailed_summary

logger = logging.getLogger(__name__)


def start_summary_task(db: Session, params: dict) -> str:
    task_id = str(uuid.uuid4())
    task = SummaryTask(
        id=task_id,
        user_id=params["user_id"],
        chat_id=params["chat_id"],
        topic_name=params.get("topic_name") or "all",
        status="pending",
        params={
            "n_results": params.get("n_results", 5),
            "max_tokens": params.get("max_tokens", 700),
        },
    )
    db.add(task)
    db.commit()
    job_queue.notify()
    return task_id


def run_summary_task(task_id: str) -> None:
    """Run one claimed summary job and store its result or error."""
    db = SessionLocal()
    try:
        task = db.get(SummaryTask, task_id)
        if task is None:
            logger.error("SummaryTask %s not found", task_id)
            return
        params = dict(task.params or {})
        result = asyncio.run(
            _build_summary(
                db,
                user_id=task.user_id,
                chat_id=task.chat_id,
                topic_name=task.topic_name or "all",
                n_results=params.get("n_results", 5),
                max_tokens=params.get("max_tokens", 700),
            )
        )
        task = db.get(SummaryTask, task_id)
        task.status = "done"
        task.result = result
        task.error = None
        task.completed_at = func.now()
        db.commit()
    except Exception as e:
        logger.exception("Summary task %s failed", task_id)
        try:
            db.rollback()
            task = db.get(SummaryTask, task_id)
            if task:
                task.status = "error"
                task.error = user_facing_error(e)
                task.completed_at = func.now()
                db.commit()
        except Exception as db_err:
            logger.error("Failed to save error status for summary task %s: %s", task_id, db_err)
    finally:
        db.close()


async def _build_summary(db: Session, *, user_id: int, chat_id: int, topic_name: str, n_results: int, max_tokens: int) -> dict:
    chat = get_chat_by_id(db, chat_id)
    if chat is None or chat.user_id != user_id:
        raise ValueError("Chat not found or doesn't belong to you")

    normalized_topic = topic_name.strip().lower() if topic_name else ""
    initial_answer = None
    if normalized_topic and normalized_topic != "all":
        initial_answer, _ = await answer_query(
            db=db,
            question=topic_name,
            user_id=user_id,
            chat_id=chat.id,
            chat_history=None,
        )

    summary, title, sections, references, chunks_used = await generate_detailed_summary(
        db=db,
        topic_name=topic_name or "all",
        user_id=user_id,
        chat_id=chat.id,
        n_results=n_results,
        max_tokens=max_tokens,
        pre_generated_answer=initial_answer,
    )
    return {
        "summary": summary,
        "topic": topic_name or "all",
        "references": [{"filename": r.get("filename", ""), "page": r.get("page", 0)} for r in references],
        "chunks_used": chunks_used,
        "title": title,
        "sections": [{"heading": s.get("heading", ""), "items": s.get("items", [])} for s in sections],
    }
