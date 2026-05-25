from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: int
    filename: str

    model_config = {"from_attributes": True}


class IngestionResponse(BaseModel):
    chunks_count: int
    status: str
    document_id: int = None
