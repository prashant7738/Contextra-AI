import asyncio
import threading
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

from app.database import SessionLocal
from app.services.retrieval_service import answer_query, generate_detailed_summary
from app.services.chat_service import get_chat


class TaskManager:
    def __init__(self):
        self._tasks: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()

    def create_task(self, task_type: str, params: dict) -> str:
        task_id = str(uuid.uuid4())
        with self._lock:
            self._tasks[task_id] = {
                "id": task_id,
                "type": task_type,
                "status": "pending",
                "params": params,
                "result": None,
                "error": None,
                "created_at": datetime.utcnow().isoformat(),
                "completed_at": None,
            }
        return task_id

    def get_task(self, task_id: str) -> Optional[dict]:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None
            return {k: v for k, v in task.items() if k != "params"}

    def update_status(self, task_id: str, status: str, result: Any = None, error: str = None):
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id]["status"] = status
                if result is not None:
                    self._tasks[task_id]["result"] = result
                if error is not None:
                    self._tasks[task_id]["error"] = error
                if status in ("done", "error"):
                    self._tasks[task_id]["completed_at"] = datetime.utcnow().isoformat()

    def _cleanup_loop(self):
        while True:
            time.sleep(300)
            cutoff = datetime.utcnow() - timedelta(hours=1)
            with self._lock:
                to_delete = [
                    tid
                    for tid, t in self._tasks.items()
                    if t.get("completed_at") and datetime.fromisoformat(t["completed_at"]) < cutoff
                ]
                for tid in to_delete:
                    del self._tasks[tid]


task_manager = TaskManager()


def start_summary_task(params: dict) -> str:
    task_id = task_manager.create_task("summary", params)
    thread = threading.Thread(
        target=_run_summary_task_sync,
        args=(task_id, params),
        daemon=True,
    )
    thread.start()
    return task_id


def _run_summary_task_sync(task_id: str, params: dict):
    try:
        task_manager.update_status(task_id, "processing")
        asyncio.run(_run_summary_task_async(task_id, params))
    except Exception as e:
        task_manager.update_status(task_id, "error", error=str(e))


async def _run_summary_task_async(task_id: str, params: dict):
    db = SessionLocal()
    try:
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
        task_manager.update_status(task_id, "done", result=result)
    except ValueError as e:
        task_manager.update_status(task_id, "error", error=str(e))
    except Exception as e:
        task_manager.update_status(task_id, "error", error=str(e))
    finally:
        db.close()
