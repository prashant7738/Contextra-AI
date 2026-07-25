import logging
import tempfile
from typing import List, Optional

from fastapi import APIRouter, UploadFile, Depends, HTTPException, File, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.schemas.user import UserResponse
from app.schemas.document import DocumentResponse
from app.schemas.ingestion_task import TaskCreatedResponse, TaskStatusResponse
from app.models.document import Document
from app.models.ingestion_task import IngestionTask
from app.services.background_ingestion import process_ingestion_task
from app.services.storage_service import create_upload_presigned_url
from app.repositories import chat_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

# Reject uploads larger than this to avoid unbounded memory/CPU use during
# OCR/embedding (and unbounded cost against the LLM/embedding provider).
MAX_UPLOAD_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB
PDF_MAGIC_BYTES = b"%PDF-"


class PresignRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)


class PresignResponse(BaseModel):
    task_id: int
    upload_url: str
    upload_method: str = "PUT"


async def _read_upload_within_limit(upload: UploadFile, max_bytes: int) -> bytes:
    """Stream-read an upload, aborting as soon as it exceeds max_bytes.

    Avoids buffering an unbounded amount of attacker-controlled data into
    memory before rejecting an oversized file.
    """
    chunks: list[bytes] = []
    total = 0
    chunk_size = 1024 * 1024
    while True:
        chunk = await upload.read(chunk_size)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File '{upload.filename}' exceeds maximum allowed size of {max_bytes // (1024 * 1024)}MB",
            )
        chunks.append(chunk)
    return b"".join(chunks)


@router.get("/", response_model=List[DocumentResponse])
def list_documents_for_chat(
    user_id: int,
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden: user mismatch")

    chat = chat_repository.get_chat_for_user(db, chat_id, user_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found or doesn't belong to you")

    docs = db.query(Document).filter(
        Document.user_id == user_id,
        Document.chat_id == chat.id
    ).all()

    return [DocumentResponse.model_validate(d) for d in docs]


@router.post("/ingest/presign", response_model=PresignResponse)
def presign_upload(
    body: PresignRequest,
    user_id: int = Query(...),
    chat_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden: user mismatch")
    if not body.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=422, detail="Only PDF files are supported")

    chat = chat_repository.get_chat_for_user(db, chat_id, user_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found or doesn't belong to you")

    upload_url, object_path = create_upload_presigned_url(body.filename)

    task = IngestionTask(
        user_id=user_id,
        chat_id=chat.id,
        filename=body.filename or "file",
        status="pending_upload",
        storage_path=object_path,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    return PresignResponse(task_id=task.id, upload_url=upload_url)


@router.post("/ingest/{task_id}/confirm", response_model=TaskCreatedResponse)
def confirm_ingest(
    task_id: int,
    background_tasks: BackgroundTasks,
    user_id: int = Query(...),
    use_ocr: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden: user mismatch")

    task = db.query(IngestionTask).filter(IngestionTask.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden: task doesn't belong to you")
    if task.status not in ("pending_upload", "pending"):
        raise HTTPException(status_code=400, detail=f"Task already {task.status}")

    task.status = "pending"
    db.commit()

    background_tasks.add_task(process_ingestion_task, task.id, use_ocr)

    return TaskCreatedResponse(task_id=task.id, status="pending")


@router.post("/ingest/direct", response_model=TaskCreatedResponse)
async def direct_ingest(
    background_tasks: BackgroundTasks,
    files: Optional[List[UploadFile]] = File(default=None),
    file: Optional[UploadFile] = File(default=None),
    user_id: int = Query(...),
    chat_id: int = Query(...),
    use_ocr: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    uploaded_files: List[UploadFile] = []
    if files:
        uploaded_files.extend(files)
    if file:
        uploaded_files.append(file)

    if not uploaded_files:
        raise HTTPException(status_code=422, detail="No file uploaded")
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden: user mismatch")

    chat = chat_repository.get_chat_for_user(db, chat_id, user_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found or doesn't belong to you")

    created_tasks: list[IngestionTask] = []
    for upload in uploaded_files:
        if not upload.filename or not upload.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=422, detail=f"Only PDF files are supported: {upload.filename or 'unknown'}")

        contents = await _read_upload_within_limit(upload, MAX_UPLOAD_SIZE_BYTES)
        if not contents.startswith(PDF_MAGIC_BYTES):
            raise HTTPException(status_code=422, detail=f"File is not a valid PDF: {upload.filename}")

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", prefix="ingest_")
        try:
            tmp.write(contents)
            tmp_path = tmp.name
        finally:
            tmp.close()

        task = IngestionTask(
            user_id=user_id,
            chat_id=chat.id,
            filename=upload.filename or "file",
            status="pending",
            file_path=tmp_path,
        )
        db.add(task)
        created_tasks.append(task)

    db.commit()

    for task in created_tasks:
        db.refresh(task)
        background_tasks.add_task(process_ingestion_task, task.id, use_ocr)

    first_task = created_tasks[0]
    return TaskCreatedResponse(task_id=first_task.id, status="pending")


@router.get("/ingest/status/{task_id}", response_model=TaskStatusResponse)
def get_ingestion_status(
    task_id: int,
    user_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden: user mismatch")

    task = db.query(IngestionTask).filter(IngestionTask.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden: task doesn't belong to you")

    return TaskStatusResponse(
        task_id=task.id,
        status=task.status,
        chunks_count=task.chunks_count,
        error_message=task.error_message,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )
