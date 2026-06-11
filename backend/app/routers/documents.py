from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, UploadFile, Depends, HTTPException, File, Query
from sqlalchemy.orm import Session
import fitz
import logging

from app.database import get_db
from app.dependencies import get_current_user
from app.schemas.user import UserResponse
from app.schemas.document import IngestionResponse, DocumentResponse
from app.models.document import Document
from app.services.ingestion_service import ingest_text
from app.services.document_service import create_document
from app.core.ocr import extract_text_hybrid
from app.repositories import chat_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


def _strip_nul_chars(text: str) -> str:
    if not text:
        return ""
    return text.replace("\x00", "")


def _background_ingest(pages_data: list, user_id: int, document_id: int, chat_id: int):
    """Run chunking + embedding + vector storage in the background."""
    try:
        count = ingest_text(pages_data, user_id=user_id, document_id=document_id, chat_id=chat_id)
        logger.info(f"Background ingestion complete: {count} chunks for document {document_id}")
    except Exception as e:
        logger.error(f"Background ingestion failed for document {document_id}: {str(e)}")


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

    # Query documents for this chat (use global chat.id)
    docs = db.query(Document).filter(
        Document.user_id == user_id,
        Document.chat_id == chat.id
    ).all()

    return [DocumentResponse.model_validate(d) for d in docs]


@router.post("/ingest", response_model=List[IngestionResponse])
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
    """
    Upload and ingest a PDF document into a specific chat.

    - use_ocr=false (default): fast path, fitz only — suitable for all text-based PDFs
    - use_ocr=true: hybrid fitz+OCR — use only for scanned/image PDFs
    
    Text extraction is synchronous; embedding/vector storage runs in background.
    """
    uploaded_files: List[UploadFile] = []
    if files:
        uploaded_files.extend(files)
    if file:
        uploaded_files.append(file)

    if not uploaded_files:
        raise HTTPException(status_code=422, detail="No file uploaded. Use 'files' or 'file' field.")

    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden: user mismatch")

    results = []
    for upload in uploaded_files:
        try:
            contents = await upload.read()
            doc = fitz.open(stream=contents, filetype="pdf")

            full_text = ""
            pages_data = []
            extraction_stats = {"fitz": 0, "ocr": 0, "failed": 0}

            logger.info(f"Processing PDF: {upload.filename} ({len(doc)} pages), use_ocr={use_ocr}")

            for page_num, page in enumerate(doc, start=1):
                text, method = extract_text_hybrid(page, page_num=page_num, use_ocr=use_ocr)
                text = _strip_nul_chars(text)
                extraction_stats[method] += 1
                full_text += text
                pages_data.append({
                    "page": page_num,
                    "text": text,
                    "filename": upload.filename,
                    "extraction_method": method
                })

            logger.info(
                f"Extraction done: {extraction_stats['fitz']} fitz, "
                f"{extraction_stats['ocr']} ocr, {extraction_stats['failed']} failed"
            )

            # Sync: create DB record (fast)
            document = create_document(db, user_id, chat_id, upload.filename, full_text)

            # Async: chunk + embed + store in vector DB
            background_tasks.add_task(
                _background_ingest, pages_data, user_id, document.id, document.chat_id
            )

            results.append(IngestionResponse(
                chunks_count=0,
                status="ingestion_queued",
                document_id=document.id,
                chat_id=chat_id,
                extraction_stats=extraction_stats
            ))
        except ValueError as e:
            logger.error(f"Validation error for {upload.filename}: {str(e)}")
            results.append(IngestionResponse(
                chunks_count=0, status=f"validation error: {str(e)}",
                document_id=None, chat_id=chat_id, extraction_stats={}
            ))
        except Exception as e:
            logger.error(f"Error processing {upload.filename}: {str(e)}")
            results.append(IngestionResponse(
                chunks_count=0, status=f"error: {str(e)}",
                document_id=None, chat_id=chat_id, extraction_stats={}
            ))

    return results
