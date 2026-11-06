"""Job queue behaviour against a real PostgreSQL database."""
import threading
import time
import uuid

import fitz
import pytest
from sqlalchemy import text

from app.core import job_queue
from app.database import SessionLocal, engine


def _db_available() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT locked_at FROM ingestion_tasks LIMIT 0"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_available(), reason="needs a migrated PostgreSQL database")

INGESTION = job_queue.KINDS[0]
SUMMARY = job_queue.KINDS[1]


@pytest.fixture
def owner():
    """A user and chat; removes everything created for them afterwards."""
    from app.models import Chat, User
    from app.repositories import chat_repository

    db = SessionLocal()
    user = User(name="q", email=f"q-{uuid.uuid4().hex[:10]}@example.com", password_hash="x",
                monthly_budget_micro_usd=10_000_000, spent_micro_usd=0)
    db.add(user)
    db.flush()
    chat = Chat(user_id=user.id, local_id=1, name="c")
    db.add(chat)
    db.commit()
    # Isolate from other rows: only this test's jobs are pending.
    db.execute(text("UPDATE ingestion_tasks SET status='failed' WHERE status IN ('pending','processing')"))
    db.execute(text("UPDATE summary_tasks SET status='error' WHERE status IN ('pending','processing')"))
    db.commit()
    yield db, user, chat
    db.rollback()
    chat_repository.delete_chat(db, chat.local_id, user.id)
    db.delete(db.get(User, user.id))
    db.commit()
    db.close()


def _pdf(tmp_path, name="n.pdf") -> str:
    doc = fitz.open()
    doc.new_page().insert_textbox(fitz.Rect(50, 50, 550, 800), "Enzymes speed up chemical reactions in cells. " * 20)
    path = tmp_path / name
    doc.save(str(path))
    return str(path)


def _add_ingestion(db, user, chat, **kw):
    from app.models import IngestionTask

    task = IngestionTask(user_id=user.id, chat_id=chat.id, filename=kw.pop("filename", "n.pdf"), status="pending", **kw)
    db.add(task)
    db.commit()
    return task.id


def test_concurrent_claims_never_take_the_same_job(owner):
    db, user, chat = owner
    ids = {_add_ingestion(db, user, chat) for _ in range(6)}
    claimed: list = []
    lock = threading.Lock()

    def claimer():
        with SessionLocal() as s:
            while True:
                job = job_queue.claim_next(s, INGESTION)
                if job is None:
                    return
                with lock:
                    claimed.append(job)

    threads = [threading.Thread(target=claimer) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(claimed) == sorted(ids)  # every job exactly once


def test_reaper_requeues_then_fails_after_max_attempts(owner):
    db, user, chat = owner
    retry = _add_ingestion(db, user, chat)
    exhausted = _add_ingestion(db, user, chat)
    fresh = _add_ingestion(db, user, chat)
    db.execute(text("UPDATE ingestion_tasks SET status='processing', locked_at=now()-interval '10 minutes', attempts=1 WHERE id=:i"), {"i": retry})
    db.execute(text("UPDATE ingestion_tasks SET status='processing', locked_at=now()-interval '10 minutes', attempts=3 WHERE id=:i"), {"i": exhausted})
    db.execute(text("UPDATE ingestion_tasks SET status='processing', locked_at=now(), attempts=1 WHERE id=:i"), {"i": fresh})
    db.commit()

    job_queue.reap_stale(db)

    rows = dict(db.execute(text("SELECT id, status FROM ingestion_tasks WHERE id IN (:a,:b,:c)"), {"a": retry, "b": exhausted, "c": fresh}).all())
    assert rows == {retry: "pending", exhausted: "failed", fresh: "processing"}


def test_worker_processes_ingestion_end_to_end(owner, tmp_path, monkeypatch):
    from app.models import Embedding, IngestionTask
    from app.services import ingestion_service

    monkeypatch.setattr(ingestion_service, "embed_texts", lambda texts: [[0.01] * 384 for _ in texts])
    db, user, chat = owner
    task_id = _add_ingestion(db, user, chat, file_path=_pdf(tmp_path))

    worker = job_queue.Worker(threads=1)
    worker.start()
    try:
        job_queue.notify()
        deadline = time.time() + 20
        while time.time() < deadline:
            db.expire_all()
            task = db.get(IngestionTask, task_id)
            if task.status in ("completed", "failed"):
                break
            time.sleep(0.2)
    finally:
        worker.stop()

    assert task.status == "completed", task.error_message
    assert task.attempts == 1 and task.chunks_count > 0
    assert db.query(Embedding).filter(Embedding.document_id == task.document_id).count() == task.chunks_count


def test_retry_discards_partial_document_from_interrupted_attempt(owner, tmp_path, monkeypatch):
    from app.models import Document, Embedding, IngestionTask
    from app.services import ingestion_service
    from app.services.background_ingestion import process_ingestion_task

    monkeypatch.setattr(ingestion_service, "embed_texts", lambda texts: [[0.02] * 384 for _ in texts])
    db, user, chat = owner
    partial = Document(user_id=user.id, chat_id=chat.id, filename="n.pdf", content="half")
    db.add(partial)
    db.commit()
    partial_id = partial.id
    db.add(Embedding(id=uuid.uuid4(), user_id=user.id, document_id=partial.id, chat_id=chat.id, content="half", embedding=[0.0] * 384))
    task_id = _add_ingestion(db, user, chat, file_path=_pdf(tmp_path), document_id=partial.id, attempts=1)

    with SessionLocal() as s:
        assert job_queue.claim_next(s, INGESTION) == task_id
    process_ingestion_task(task_id)

    db.expire_all()
    task = db.get(IngestionTask, task_id)
    assert task.status == "completed" and task.attempts == 2
    assert db.get(Document, partial_id) is None
    assert db.query(Embedding).filter(Embedding.document_id == partial_id).count() == 0
    assert db.query(Document).filter(Document.chat_id == chat.id).count() == 1


def test_summary_job_runs_from_persisted_params(owner, monkeypatch):
    from app import tasks
    from app.models import SummaryTask

    seen = {}

    async def fake_build(db, **kwargs):
        seen.update(kwargs)
        return {"summary": "s", "topic": kwargs["topic_name"], "references": [], "chunks_used": 1, "title": "T", "sections": []}

    monkeypatch.setattr(tasks, "_build_summary", fake_build)
    monkeypatch.setattr(job_queue, "notify", lambda: None)
    db, user, chat = owner
    task_id = tasks.start_summary_task(db, {"user_id": user.id, "chat_id": chat.id, "topic_name": "enzymes", "n_results": 9, "max_tokens": 500})

    with SessionLocal() as s:
        assert job_queue.run_one(s, SUMMARY) is True

    db.expire_all()
    task = db.get(SummaryTask, task_id)
    assert task.status == "done" and task.result["title"] == "T"
    assert seen == {"user_id": user.id, "chat_id": chat.id, "topic_name": "enzymes", "n_results": 9, "max_tokens": 500}


def test_missing_direct_upload_file_fails_with_clear_message(owner):
    from app.models import IngestionTask
    from app.services.background_ingestion import process_ingestion_task

    db, user, chat = owner
    task_id = _add_ingestion(db, user, chat, file_path="/nonexistent/ingest_gone.pdf")
    process_ingestion_task(task_id)
    db.expire_all()
    task = db.get(IngestionTask, task_id)
    assert task.status == "failed"
    assert "no longer available" in task.error_message
