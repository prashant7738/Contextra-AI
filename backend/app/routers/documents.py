import logging
import tempfile
from typing import List, Optional

from fastapi import APIRouter, UploadFile, Depends, HTTPException, File, Query, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.schemas.user import UserResponse
from app.schemas.document import DocumentResponse
from app.schemas.ingestion_task import TaskCreatedResponse, TaskStatusResponse
from app.models.document import Document
from app.models.ingestion_task import IngestionTask
from app.services.background_ingestion import process_ingestion_task
from app.repositories import chat_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


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


@router.post("/ingest", response_model=TaskCreatedResponse)
async def file_input(
    background_tasks: BackgroundTasks,
    files: Optional[List[UploadFile]] = File(default=None),
    file: Optional[UploadFile] = File(default=None),
    user_id: int = Query(...),
    chat_id: int = Query(...),
    use_ocr: bool = Query(default=False, description="Enable OCR fallback for scanned PDFs (slow on CPU)"),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    uploaded_files: List[UploadFile] = []
    if files:
        uploaded_files.extend(files)
    if file:
        uploaded_files.append(file)

    if not uploaded_files:
        raise HTTPException(status_code=422, detail="No file uploaded. Use 'files' or 'file' field.")

    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden: user mismatch")

    upload = uploaded_files[0]
    contents = await upload.read()

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", prefix=f"ingest_")
    try:
        tmp.write(contents)
        tmp_path = tmp.name
    finally:
        tmp.close()

    task = IngestionTask(
        user_id=user_id,
        chat_id=chat_id,
        filename=upload.filename or "file",
        status="pending",
        file_path=tmp_path,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    background_tasks.add_task(process_ingestion_task, task.id, use_ocr)

    return TaskCreatedResponse(task_id=task.id, status="pending")


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
