from app.core.embedder import embed_texts
from app.core.llm import ask_detailed_summary_llm, ask_llm
from app.repositories.vector_repository import query_similar


def answer_query(question: str, user_id: int, chat_id: int, chat_history: list = None) -> tuple[str, list[dict]]:
    """
    Answer a query within a specific chat context.
    
    Args:
        question: The query question
        user_id: ID of the user asking (for access control)
        chat_id: ID of the chat (for context filtering)
        chat_history: Previous messages in the chat (optional, for context)
    
    Returns:
        Tuple of (answer, references) where references are the source chunks used
    """
    query_embedding = embed_texts([question])[0]
    results = query_similar(query_embedding, n_results=10, user_id=user_id, chat_id=chat_id)
    context = "\n\n".join(results.get("documents", [[]])[0])
    references = _extract_references(results)
    
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
    return ask_llm(full_context, question), references


def generate_detailed_summary(
    topic_name: str,
    user_id: int,
    chat_id: int,
    n_results: int = 20,
    max_tokens: int = 700,
) -> tuple[str, list[dict], int]:
    """
    Generate a detailed 80/20 study summary from chat-scoped uploaded notes.

    Args:
        topic_name: Topic to summarize or "all" for full notes
        user_id: ID of the user (for access control)
        chat_id: ID of the chat (for context filtering)
        n_results: Number of chunks to retrieve from vector store
        max_tokens: Max tokens for LLM output

    Returns:
        Tuple of (summary, references, chunks_used)

    Raises:
        ValueError: If no content is found for chat/topic
    """
    normalized_topic = topic_name.strip()
    retrieval_query = (
        "Provide a high-yield summary of these study notes"
        if normalized_topic.lower() == "all"
        else normalized_topic
    )

    query_embedding = embed_texts([retrieval_query])[0]
    results = query_similar(query_embedding, n_results=n_results, user_id=user_id, chat_id=chat_id)

    docs = results.get("documents", [[]])[0]
    if not docs:
        raise ValueError("No uploaded notes found in this chat")

    if normalized_topic.lower() != "all":
        topic_lower = normalized_topic.lower()
        if not any(topic_lower in doc.lower() for doc in docs):
            raise ValueError("Topic not found in uploaded notes for this chat")

    context = "\n\n".join(docs)
    references = _extract_references(results)
    summary = ask_detailed_summary_llm(context, normalized_topic, max_tokens=max_tokens)
    return summary, references, len(docs)


def _extract_references(results: dict) -> list[dict]:
    references: list[dict] = []
    seen = set()
    for meta in results.get("metadatas", [[]])[0]:
        key = (meta.get("filename", "unknown"), meta.get("page", 0))
        if key in seen:
            continue
        seen.add(key)
        references.append(
            {
                "filename": meta.get("filename", "unknown"),
                "page": meta.get("page", 0),
                "document_id": meta.get("document_id"),
            }
        )
    return references
