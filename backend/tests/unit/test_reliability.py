import os
from unittest.mock import MagicMock

import fitz
import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.core.chunker import chunk_document
from app.repositories import chat_repository
from app.services import background_ingestion
from app.services.background_ingestion import GENERIC_INGESTION_ERROR, user_facing_error


def test_user_facing_error_hides_internal_details():
    assert user_facing_error(RuntimeError("psycopg2 connection to 10.0.0.5 refused")) == GENERIC_INGESTION_ERROR
    assert user_facing_error(ValueError("No readable text")) == "No readable text"
    assert user_facing_error(HTTPException(429, "Daily AI budget reached.")) == "Daily AI budget reached."
    assert user_facing_error(fitz.FileDataError("bad")) == "The file could not be read as a PDF."


def test_chunker_skips_blank_pages():
    chunks = chunk_document(
        [
            {"page": 1, "text": "   ", "filename": "a.pdf"},
            {"page": 2, "text": "Hello world.", "filename": "a.pdf"},
            {"page": 3, "text": None, "filename": "a.pdf"},
        ],
        chunk_size=50,
    )
    assert chunks == [{"text": "Hello world.", "page": 2, "filename": "a.pdf"}]


class _FakeTask:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def _run_ingestion(monkeypatch, tmp_path, *, storage_path=None, fail=False):
    pdf = fitz.open()
    pdf.new_page().insert_text((72, 72), "Some words long enough to count as real text here.")
    local = tmp_path / "ingest_test.pdf"
    pdf.save(str(local))

    task = _FakeTask(
        id=1, status="pending", storage_path=storage_path, file_path=None if storage_path else str(local),
        user_id=1, chat_id=2, filename="t.pdf", chunks_count=0, error_message=None,
        document_id=None, use_ocr=False, attempts=1,
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = task
    monkeypatch.setattr(background_ingestion, "SessionLocal", lambda: db)
    monkeypatch.setattr(background_ingestion, "download_file", lambda path: str(local))
    monkeypatch.setattr(background_ingestion, "create_document", lambda *a, **k: _FakeTask(id=5, chat_id=2))

    def fake_ingest(*a, **k):
        if fail:
            raise RuntimeError("secret internal failure")
        return 3

    monkeypatch.setattr(background_ingestion, "ingest_text", fake_ingest)
    background_ingestion.process_ingestion_task(1)
    return task, local


@pytest.mark.parametrize("storage_path", [None, "uploads/abc_t.pdf"])
def test_ingestion_always_removes_local_temp_file(monkeypatch, tmp_path, storage_path):
    task, local = _run_ingestion(monkeypatch, tmp_path, storage_path=storage_path)
    assert task.status == "completed"
    assert task.chunks_count == 3
    assert not os.path.exists(local)


def test_ingestion_failure_stores_generic_message_and_cleans_up(monkeypatch, tmp_path):
    task, local = _run_ingestion(monkeypatch, tmp_path, storage_path="uploads/x.pdf", fail=True)
    assert task.status == "failed"
    assert task.error_message == GENERIC_INGESTION_ERROR
    assert not os.path.exists(local)


def test_create_chat_retries_on_local_id_collision():
    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
    db.commit.side_effect = [IntegrityError("x", {}, Exception()), None]
    chat = chat_repository.create_chat(db, user_id=1, name="n")
    assert chat.name == "n"
    assert db.rollback.call_count == 1
    assert db.commit.call_count == 2
