from typing import Optional
from datetime import datetime

from pydantic import BaseModel


class TaskCreatedResponse(BaseModel):
    task_id: int
    status: str


class TaskStatusResponse(BaseModel):
    task_id: int
    status: str
    chunks_count: int = 0
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
