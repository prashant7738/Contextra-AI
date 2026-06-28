import logging
import os

import fitz

from app.database import SessionLocal
from app.models.ingestion_task import IngestionTask
from app.services.ingestion_service import ingest_text
from app.services.document_service import create_document
from app.core.ocr import extract_text_hybrid

logger = logging.getLogger(__name__)


def _strip_nul_chars(text: str) -> str:
    if not text:
        return ""
    return text.replace("\x00", "")


def process_ingestion_task(task_id: int, use_ocr: bool = False) -> None:
    db = SessionLocal()
    task = None
    try:
        task = db.query(IngestionTask).filter(IngestionTask.id == task_id).first()
        if not task:
            logger.error(f"IngestionTask {task_id} not found")
            return
        if task.status != "pending":
            logger.warning(f"IngestionTask {task_id} already {task.status}, skipping")
            return

        task.status = "processing"
        db.commit()

        if not task.file_path or not os.path.exists(task.file_path):
            raise FileNotFoundError(f"File not found at {task.file_path}")

        with open(task.file_path, "rb") as f:
            contents = f.read()

        doc = fitz.open(stream=contents, filetype="pdf")

        full_text = ""
        pages_data = []
        extraction_stats = {"fitz": 0, "ocr": 0, "failed": 0}

        logger.info(f"Processing PDF: {task.filename} ({len(doc)} pages), use_ocr={use_ocr}")

        for page_num, page in enumerate(doc, start=1):
            text, method = extract_text_hybrid(page, page_num=page_num, use_ocr=use_ocr)
            text = _strip_nul_chars(text)
            extraction_stats[method] += 1
            full_text += text
            pages_data.append({
                "page": page_num,
                "text": text,
                "filename": task.filename,
                "extraction_method": method,
            })

        logger.info(f"Extraction done: {extraction_stats}")

        document = create_document(db, task.user_id, task.chat_id, task.filename, full_text)
        chunks_count = ingest_text(
            pages_data,
            user_id=task.user_id,
            document_id=document.id,
            chat_id=document.chat_id,
        )

        logger.info(f"Document {document.id} ingested: {chunks_count} chunks")

        task.status = "completed"
        task.chunks_count = chunks_count
        task.error_message = None
        db.commit()

    except Exception as e:
        logger.error(f"Error processing ingestion task {task_id}: {str(e)}")
        if task is not None:
            try:
                task.status = "failed"
                task.error_message = str(e)
                db.commit()
            except Exception as db_err:
                logger.error(f"Failed to update task {task_id} status: {str(db_err)}")
    finally:
        if task is not None and task.file_path and os.path.exists(task.file_path):
            try:
                os.remove(task.file_path)
            except Exception as e:
                logger.warning(f"Failed to remove temp file {task.file_path}: {e}")
        db.close()
