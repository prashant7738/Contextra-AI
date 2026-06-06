from app.core.embedder import embed_texts
from app.core.llm import ask_detailed_summary_llm, ask_llm, generate_flashcards_llm
from app.repositories.vector_repository import query_similar
import json


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
    n_results: int = 5,
    max_tokens: int = 700,
    pre_generated_answer: str = None,
) -> tuple[str, list[dict], int]:
    """
    Generate a detailed study summary from uploaded notes using 80-20 rule. i.e. give 20% information which covers 80% of the important topic.
    Answer it in your own language even by adding more information you know.

    Args:
        topic_name: Topic to summarize or "all" for full notes
        user_id: ID of the user (for access control)
        chat_id: ID of the chat (for context filtering)
        n_results: Number of chunks to retrieve from vector store
        max_tokens: Max tokens for LLM output
        pre_generated_answer: Optional LLM-generated answer from answer_query to use as base context

    Returns:
        Tuple of (summary, references, chunks_used)

    Raises:
        ValueError: If no exact content is found for chat/topic
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
    
    # Note: For topic searches beyond "all", the vector similarity search 
    # already filtered for relevant documents. Removing strict substring 
    # validation to handle typos and semantic variations.

    context = "\n\n".join(docs)
    references = _extract_references(results)
    
    # If a pre-generated answer exists, include it in the context
    # This gives the LLM the initial query result to expand upon
    if pre_generated_answer:
        full_context = f"Initial Query Response:\n{pre_generated_answer}\n\n---\n\nSource Documents:\n{context}"
    else:
        full_context = context
    
    summary = ask_detailed_summary_llm(full_context, normalized_topic, max_tokens=max_tokens)
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


def generate_flashcards(
    user_id: int,
    chat_id: int,
    n_results: int = 5,
    max_tokens: int = 1000,
) -> tuple[list[dict], list[dict]]:
    """
    Generate multiple flashcards from all uploaded notes using smart distribution.
    
    Args:
        user_id: ID of the user (for access control)
        chat_id: ID of the chat (for context filtering)
        n_results: Number of chunks to retrieve from vector store
        max_tokens: Max tokens for LLM output
    
    Returns:
        Tuple of (flashcards, references) where:
        - flashcards: List of dicts with topic, summary, explanation
        - references: List of unique document references used
    
    Raises:
        ValueError: If no content found or JSON parsing fails
    """
    # Step 1: Get all content from the chat
    retrieval_query = "Provide a high-yield summary of these study notes"
    query_embedding = embed_texts([retrieval_query])[0]
    results = query_similar(query_embedding, n_results=n_results, user_id=user_id, chat_id=chat_id)
    
    docs = results.get("documents", [[]])[0]
    if not docs:
        raise ValueError("No uploaded notes found in this chat")
    
    context = "\n\n".join(docs)
    references = _extract_references(results)
    
    # Step 2: Generate flashcards using LLM
    flashcards_json = generate_flashcards_llm(context, max_tokens=max_tokens)
    
    # Step 3: Parse JSON response with robust error handling
    try:
        # Find JSON object boundaries
        json_start = flashcards_json.find('{')
        json_end = flashcards_json.rfind('}') + 1
        
        if json_start < 0 or json_end <= json_start:
            raise ValueError("No JSON object found in response")
        
        json_str = flashcards_json[json_start:json_end].strip()
        
        # Try parsing
        parsed = json.loads(json_str)
        flashcards = parsed.get("flashcards", [])
        
        if not flashcards:
            raise ValueError("No flashcards found in parsed JSON")
        
        # Validate and clean flashcard data
        cleaned_flashcards = []
        for fc in flashcards:
            if not isinstance(fc, dict):
                continue
            
            # Ensure required fields exist
            if not fc.get("topic") or not fc.get("summary") or not fc.get("explanation"):
                continue
            
            cleaned_flashcards.append({
                "topic": str(fc.get("topic", "")).strip(),
                "summary": str(fc.get("summary", "")).strip(),
                "explanation": str(fc.get("explanation", "")).strip(),
                "references": references,
            })
        
        if not cleaned_flashcards:
            raise ValueError("No valid flashcards after validation")
        
        return cleaned_flashcards, references
    
    except json.JSONDecodeError as e:
        # Log more details for debugging
        raise ValueError(
            f"Failed to parse flashcard JSON (at position {e.pos}): {str(e)}\n"
            f"Response preview: {flashcards_json[:500]}..."
        )
