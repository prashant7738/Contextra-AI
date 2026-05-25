from fastapi import APIRouter

from app.schemas.chat import QueryRequest, ChatResponse
from app.services.retrieval_service import answer_query

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/", response_model=ChatResponse)
def chat(query: QueryRequest):
    answer = answer_query(query.request)
    return ChatResponse(answer=answer)
