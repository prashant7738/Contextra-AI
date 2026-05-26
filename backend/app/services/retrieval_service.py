from app.core.embedder import embed_texts
from app.core.llm import ask_llm
from app.repositories.vector_repository import query_similar


def answer_query(question: str, user_id: int, chat_id: int) -> str:
    """
    Answer a query within a specific chat context.
    
    Args:
        question: The query question
        user_id: ID of the user asking (for access control)
        chat_id: ID of the chat (for context filtering)
    
    Returns:
        The LLM answer based on chat-specific context
    """
    query_embedding = embed_texts([question])[0]
    results = query_similar(query_embedding, n_results=3, user_id=user_id, chat_id=chat_id)
    context = "\n".join(results["documents"][0])
    return ask_llm(context, question)
