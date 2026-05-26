from app.core.embedder import embed_texts
from app.core.llm import ask_llm
from app.repositories.vector_repository import query_similar


def answer_query(question: str, user_id: int, chat_id: int, chat_history: list = None) -> str:
    """
    Answer a query within a specific chat context.
    
    Args:
        question: The query question
        user_id: ID of the user asking (for access control)
        chat_id: ID of the chat (for context filtering)
        chat_history: Previous messages in the chat (optional, for context)
    
    Returns:
        The LLM answer based on chat-specific context and history
    """
    query_embedding = embed_texts([question])[0]
    results = query_similar(query_embedding, n_results=3, user_id=user_id, chat_id=chat_id)
    context = "\n".join(results["documents"][0])
    
    # Build conversation history context if available
    history_context = ""
    if chat_history:
        history_lines = []
        for msg in chat_history:
            history_lines.append(f"User: {msg.user_message}")
            history_lines.append(f"Assistant: {msg.bot_response}")
        history_context = "\n\nPrevious conversation:\n" + "\n".join(history_lines)
    
    # Combine contexts: history + document context
    full_context = context + history_context
    return ask_llm(full_context, question)
