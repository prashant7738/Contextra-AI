from pydantic import BaseModel


class QueryRequest(BaseModel):
    request: str


class ChatResponse(BaseModel):
    answer: str
