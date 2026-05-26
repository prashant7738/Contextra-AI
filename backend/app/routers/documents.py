from fastapi import APIRouter, UploadFile, Depends, HTTPException, File, Query
from sqlalchemy.orm import Session
import fitz

from app.database import get_db
from app.schemas.document import IngestionResponse
from app.services.ingestion_service import ingest_text
from app.services.document_service import create_document

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/ingest", response_model=IngestionResponse)
async def file_input(file: UploadFile = File(...), user_id: int = Query(...), chat_id: int = Query(...), db: Session = Depends(get_db)):
    """
    Upload and ingest a PDF document into a specific chat.
    
    Args:
        file: PDF file to upload
        user_id: ID of the user uploading the document
        chat_id: ID of the chat to attach the document to
        db: Database session
    """
    try:
        contents = await file.read()
        doc = fitz.open(stream=contents, filetype="pdf")
        
        # Extract all text for database storage
        full_text = ""
        pages_data = []
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text()
            full_text += text
            pages_data.append({
                "page": page_num,
                "text": text,
                "filename": file.filename
            })
        
        # Create document record in database
        document = create_document(db, user_id, chat_id, file.filename, full_text)
        
        # Ingest into vector database with user_id, document_id, and chat_id
        chunks_count = ingest_text(pages_data, user_id=user_id, document_id=document.id, chat_id=chat_id)
        
        return IngestionResponse(
            chunks_count=chunks_count,
            status="embedded and stored",
            document_id=document.id,
            chat_id=chat_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")
