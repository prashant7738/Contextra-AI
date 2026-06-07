from pydantic import BaseModel, Field, field_validator
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


class SummarySection(BaseModel):
    heading: str
    items: list[str] = []


class QueryRequest(BaseModel):
    chat_id: int
    request: str


class QueryResponse(BaseModel):
    answer: str
    references: list[Reference] = []
    conversation_history: Optional[list[ChatMessageResponse]] = None


class DetailedSummaryRequest(BaseModel):
    chat_id: int
    topic_name: str = "all"
    n_results: int = Field(default=5, ge=3, le=40)
    max_tokens: int = Field(default=700, ge=200, le=1200)

    @field_validator("topic_name")
    @classmethod
    def validate_topic_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("topic_name cannot be empty")
        return cleaned


class DetailedSummaryResponse(BaseModel):
    summary: str
    topic: str
    references: list[Reference] = []
    chunks_used: int
    title: Optional[str] = None
    sections: list[SummarySection] = []


class Flashcard(BaseModel):
    topic: str
    summary: str
    explanation: str
    references: list[Reference] = []


class FlashcardRequest(BaseModel):
    n_results: int = Field(default=5, ge=3, le=40)
    max_tokens: int = Field(default=1000, ge=500, le=2000)


class FlashcardResponse(BaseModel):
    flashcards: list[Flashcard]
    total_topics: int
    total_flashcards: int
