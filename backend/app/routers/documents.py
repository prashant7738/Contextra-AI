from typing import List, Optional

from fastapi import APIRouter, UploadFile, Depends, HTTPException, File, Query
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

# Initialize logger
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


def _strip_nul_chars(text: str) -> str:
    """Remove NUL bytes that can break DB inserts and downstream storage."""
    if not text:
        return ""
    return text.replace("\x00", "")


@router.get("/", response_model=List[DocumentResponse])
def list_documents_for_chat(user_id: int, chat_id: int, db: Session = Depends(get_db), current_user: UserResponse = Depends(get_current_user)):
    """
    List documents attached to a chat for the current user.
    """
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden: user mismatch")

    # Resolve chat (chat_id is the user's local_id) -> get global chat.id
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
    files: Optional[List[UploadFile]] = File(default=None),
    file: Optional[UploadFile] = File(default=None),
    user_id: int = Query(...),
    chat_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Upload and ingest a PDF document into a specific chat.
    
    Supports both digital and scanned PDFs:
    - Digital PDFs: Fast text extraction via fitz
    - Scanned PDFs: OCR-based text extraction (slower, but accurate)
    
    Args:
        files: PDF files to upload (preferred multipart field)
        file: Single PDF file upload field (backward compatibility)
        user_id: ID of the user uploading the document
        chat_id: ID of the chat to attach the document to
        db: Database session
    """
    uploaded_files: List[UploadFile] = []
    if files:
        uploaded_files.extend(files)
    if file:
        uploaded_files.append(file)

    if not uploaded_files:
        raise HTTPException(status_code=422, detail="No file uploaded. Use multipart field 'files' (preferred) or 'file'.")

    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden: user mismatch")

    results = []
    # Process each uploaded file sequentially
    for file in uploaded_files:
        try:
            contents = await file.read()
            doc = fitz.open(stream=contents, filetype="pdf")

            # Extract all text for database storage
            full_text = ""
            pages_data = []
            extraction_stats = {"fitz": 0, "ocr": 0, "failed": 0}

            logger.info(f"Processing PDF: {file.filename} ({len(doc)} pages)")

            for page_num, page in enumerate(doc, start=1):
                # Use hybrid extraction: fitz first, OCR as fallback
                text, method = extract_text_hybrid(page, page_num=page_num)
                text = _strip_nul_chars(text)
                extraction_stats[method] += 1

                full_text += text
                pages_data.append({
                    "page": page_num,
                    "text": text,
                    "filename": file.filename,
                    "extraction_method": method
                })

                logger.debug(f"Page {page_num}: extracted via {method}")

            # Log extraction summary
            logger.info(
                f"PDF processing complete: {extraction_stats['fitz']} pages via fitz, "
                f"{extraction_stats['ocr']} via OCR, {extraction_stats['failed']} failed"
            )

            # Create document record in database (create_document will resolve chat local_id to global id)
            document = create_document(db, user_id, chat_id, file.filename, full_text)

            # Ingest into vector database with user_id, document_id, and global chat_id
            chunks_count = ingest_text(pages_data, user_id=user_id, document_id=document.id, chat_id=document.chat_id)

            logger.info(f"Document ingested: {chunks_count} chunks created")

            results.append(IngestionResponse(
                chunks_count=chunks_count,
                status="embedded and stored",
                document_id=document.id,
                chat_id=chat_id,
                extraction_stats=extraction_stats
            ))
        except ValueError as e:
            logger.error(f"Validation error for file {file.filename}: {str(e)}")
            results.append(IngestionResponse(chunks_count=0, status=f"validation error: {str(e)}", document_id=None, chat_id=chat_id, extraction_stats={}))
        except Exception as e:
            logger.error(f"Error processing PDF {file.filename}: {str(e)}")
            results.append(IngestionResponse(chunks_count=0, status=f"error: {str(e)}", document_id=None, chat_id=chat_id, extraction_stats={}))

    return results
