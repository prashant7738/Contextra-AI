import asyncio
from app.core.embedder import embed_texts
from app.core.llm import ask_detailed_summary_llm, ask_llm, generate_flashcards_llm
from app.repositories.pgvector_repository import query_similar
from app.services.flashcard_parsing import (
    parse_flashcard_json_fallback,
    parse_flashcard_marker_output,
)
import json
import re


async def answer_query(question: str, user_id: int, chat_id: int, chat_history: list = None) -> tuple[str, list[dict]]:
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
    query_embedding = (await asyncio.to_thread(embed_texts, [question]))[0]
    results = await asyncio.to_thread(query_similar, query_embedding, 10, user_id, chat_id)
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
    return await ask_llm(full_context, question), references


async def generate_detailed_summary(
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

    query_embedding = (await asyncio.to_thread(embed_texts, [retrieval_query]))[0]
    results = await asyncio.to_thread(query_similar, query_embedding, n_results, user_id, chat_id)

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
    
    summary_output = await ask_detailed_summary_llm(full_context, normalized_topic, max_tokens=max_tokens)
    summary, title, sections = _parse_detailed_summary_output(summary_output, normalized_topic)
    return summary, title, sections, references, len(docs)


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


def _parse_detailed_summary_output(output: str, topic_name: str) -> tuple[str, str, list[dict]]:
    cleaned = output.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        data = json.loads(cleaned)
        sections = []
        for section in data.get("sections", []):
            heading = str(section.get("heading", "")).strip()
            items = [str(item).strip() for item in section.get("items", []) if str(item).strip()]
            if heading and items:
                sections.append({"heading": heading, "items": items})
        title = str(data.get("title", "")).strip() or f"Detailed summary: {topic_name}"
        summary = _format_detailed_summary_text(title, sections)
        return summary, title, sections
    except (json.JSONDecodeError, TypeError, AttributeError):
        pass

    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    sections = []
    current = None
    title = f"Detailed summary: {topic_name}"

    for line in lines:
        line = line.replace("**", "")
        line = re.sub(r"^\s{0,3}#{1,6}\s*", "", line)
        heading_match = re.match(r"^(?:\d+[).]\s*)?([A-Za-z][A-Za-z0-9 /&-]+):?\s*$", line)
        if heading_match and len(line) < 80:
            heading = heading_match.group(1).strip()
            current = {"heading": heading, "items": []}
            sections.append(current)
            if not title or title == f"Detailed summary: {topic_name}":
                title = heading
            continue

        if re.match(r"^[\-*•]\s+", line):
            item = re.sub(r"^[\-*•]\s+", "", line).strip()
            if current is None:
                current = {"heading": "Summary", "items": []}
                sections.append(current)
            current["items"].append(item)
            continue

        if current is None:
            current = {"heading": "Summary", "items": []}
            sections.append(current)
        current["items"].append(line)

    summary = _format_detailed_summary_text(title, sections)
    return summary, title, sections


def _format_detailed_summary_text(title: str, sections: list[dict]) -> str:
    lines = [title]
    for section in sections:
        heading = section.get("heading", "").strip()
        items = section.get("items", [])
        if not heading:
            continue
        lines.append("")
        lines.append(heading)
        for item in items:
            clean_item = str(item).strip()
            if clean_item:
                lines.append(f"- {clean_item}")
    return "\n".join(lines).strip()


async def generate_flashcards(
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
    flashcards_output = await generate_flashcards_llm(context, max_tokens=max_tokens)
    
    # Step 3: Parse response in marker format first, then JSON as fallback
    cleaned_flashcards = parse_flashcard_marker_output(flashcards_output)
    if not cleaned_flashcards:
        cleaned_flashcards = parse_flashcard_json_fallback(flashcards_output)

    if not cleaned_flashcards:
        raise ValueError(
            "Failed to parse flashcards from model output. "
            f"Response preview: {flashcards_output[:400]}..."
        )

    # Attach references
    for card in cleaned_flashcards:
        card["references"] = references

    return cleaned_flashcards, references
