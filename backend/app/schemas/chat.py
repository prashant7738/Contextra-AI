from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ChatCreate(BaseModel):
    name: str


class ChatResponse(BaseModel):
    id: int
    user_id: int
    name: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatMessageResponse(BaseModel):
    id: int
    chat_id: int
    user_message: str
    bot_response: str
    created_at: datetime

    model_config = {"from_attributes": True}


class Reference(BaseModel):
    filename: str
    page: int
    document_id: Optional[int] = None


class QueryRequest(BaseModel):
    chat_id: int
    request: str


class QueryResponse(BaseModel):
    answer: str
    references: list[Reference] = []
    conversation_history: Optional[list[ChatMessageResponse]] = None
