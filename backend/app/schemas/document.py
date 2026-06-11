from typing import Optional

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: int
    chat_id: int
    filename: str

    model_config = {"from_attributes": True}


class IngestionResponse(BaseModel):
    chunks_count: int
    status: str
    document_id: Optional[int] = None
    chat_id: Optional[int] = None
    extraction_stats: Optional[dict] = None  # Shows {fitz: X, ocr: Y, failed: Z}
