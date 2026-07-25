from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

from app.schemas.chat import Reference


class QuizRequest(BaseModel):
    num_questions: int = Field(default=5, ge=5, le=20)
    max_tokens: int = Field(default=1500, ge=500, le=3000)


class QuizQuestionPublic(BaseModel):
    """Question shape sent to the client before they submit answers - no correct answer."""
    question: str
    options: list[str]


class QuizGenerateResponse(BaseModel):
    quiz_id: int
    chat_id: int
    num_questions: int
    questions: list[QuizQuestionPublic]
    created_at: datetime


class QuizSubmitRequest(BaseModel):
    answers: list[int] = Field(..., description="Selected option index per question, -1 if unanswered")


class QuizQuestionResult(BaseModel):
    question: str
    options: list[str]
    selected_index: int
    correct_index: int
    is_correct: bool
    explanation: str
    references: list[Reference] = []


class QuizSubmitResponse(BaseModel):
    quiz_id: int
    score: int
    total_questions: int
    results: list[QuizQuestionResult]
    submitted_at: datetime


class QuizHistoryItem(BaseModel):
    quiz_id: int
    num_questions: int
    created_at: datetime
    last_score: Optional[int] = None
    last_total_questions: Optional[int] = None
    last_submitted_at: Optional[datetime] = None
