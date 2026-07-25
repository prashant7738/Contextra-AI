import asyncio
from app.core.embeddings import embed_texts
from app.core.llm import ask_detailed_summary_llm, ask_llm, generate_flashcards_llm, generate_quiz_llm
from app.repositories.pgvector_repository import query_similar
from app.services.flashcard_parsing import (
    parse_flashcard_json_fallback,
    parse_flashcard_marker_output,
)
from app.services.quiz_parsing import (
    parse_quiz_json_fallback,
    parse_quiz_marker_output,
)
from app.services.token_budget_service import consume_user_tokens, estimate_token_cost
import json
import re
from sqlalchemy.orm import Session


BROAD_FALLBACK_QUERY = "Provide a high-yield summary of these study notes"

_FILENAME_HINT_PATTERN = re.compile(r"(?:\b|['\"])([A-Za-z0-9_-]+(?:\.pdf)?)(?:\b|['\"])", re.IGNORECASE)


async def _retrieve_context(
    queries: list[str],
    user_id: int,
    chat_id: int,
    n_results: int,
) -> tuple[list[str], list[dict]]:
    documents: list[str] = []
    references: list[dict] = []
    seen = set()

    for query in queries:
        normalized_query = query.strip()
        if not normalized_query:
            continue

        query_embedding = (await asyncio.to_thread(embed_texts, [normalized_query]))[0]
        results = await asyncio.to_thread(query_similar, query_embedding, n_results, user_id, chat_id)

        for document, metadata in zip(results.get("documents", [[]])[0], results.get("metadatas", [[]])[0]):
            cleaned_document = str(document).strip()
            if not cleaned_document:
                continue

            reference_key = (
                cleaned_document,
                metadata.get("filename", "unknown"),
                metadata.get("page", 0),
                metadata.get("document_id"),
            )
            if reference_key in seen:
                continue

            seen.add(reference_key)
            documents.append(cleaned_document)
            references.append(
                {
                    "filename": metadata.get("filename", "unknown"),
                    "page": metadata.get("page", 0),
                    "document_id": metadata.get("document_id"),
                }
            )

    return documents, references


async def answer_query(
    db: Session,
    question: str,
    user_id: int,
    chat_id: int,
    chat_history: list = None,
    max_tokens: int = 800,
) -> tuple[str, list[dict]]:
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
    docs, references = await _retrieve_context(
        queries=_build_question_queries(question),
        user_id=user_id,
        chat_id=chat_id,
        n_results=max(10, max_tokens // 80),
    )

    if not docs:
        raise ValueError("No uploaded notes found in this chat")

    context = _format_context_with_references(docs, references)
    
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
    consume_user_tokens(db, user_id, estimate_token_cost(full_context, question, max_tokens=max_tokens))
    return await ask_llm(full_context, question, max_tokens=max_tokens), references


def _format_context_with_references(docs: list[str], references: list[dict]) -> str:
    blocks: list[str] = []
    for index, doc in enumerate(docs):
        reference = references[index] if index < len(references) else {}
        filename = reference.get("filename", "unknown")
        page = reference.get("page", 0)
        blocks.append(f"[Source: {filename} p.{page}]\n{doc}")
    return "\n\n".join(blocks)


def _build_question_queries(question: str) -> list[str]:
    filename_queries = _extract_filename_queries(question)
    queries = filename_queries + [question] if filename_queries else [question]
    queries.append(BROAD_FALLBACK_QUERY)
    return _dedupe_text_list(queries)


def _extract_filename_queries(question: str) -> list[str]:
    lowered = question.lower()
    hints: list[str] = []

    for match in _FILENAME_HINT_PATTERN.finditer(question):
        token = match.group(1).strip().strip(".,:;!?)")
        if not token:
            continue

        normalized = token.lower()
        if normalized.endswith(".pdf"):
            hints.append(normalized)
        elif "file" in lowered and any(ch.isdigit() for ch in normalized):
            hints.extend([normalized, f"{normalized}.pdf"])

    return _dedupe_text_list(hints)


async def generate_detailed_summary(
    db: Session,
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
    if normalized_topic.lower() == "all":
        retrieval_queries = [
            BROAD_FALLBACK_QUERY,
            "List all major topics and subtopics from these study notes",
        ]
        search_limit = max(n_results, 12)
    else:
        retrieval_queries = [
            normalized_topic,
            f"{normalized_topic} study notes",
            BROAD_FALLBACK_QUERY,
        ]
        search_limit = max(n_results, 8)

    docs, references = await _retrieve_context(
        queries=retrieval_queries,
        user_id=user_id,
        chat_id=chat_id,
        n_results=search_limit,
    )

    if not docs:
        raise ValueError("No uploaded notes found in this chat")

    context = "\n\n".join(docs)
    
    # If a pre-generated answer exists, include it in the context
    # This gives the LLM the initial query result to expand upon
    if pre_generated_answer:
        full_context = f"Initial Query Response:\n{pre_generated_answer}\n\n---\n\nSource Documents:\n{context}"
    else:
        full_context = context
    
    consume_user_tokens(db, user_id, estimate_token_cost(full_context, normalized_topic, max_tokens=max_tokens))
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
        section_index: dict[str, dict] = {}
        for section in data.get("sections", []):
            heading = str(section.get("heading", "")).strip()
            items = [str(item).strip() for item in section.get("items", []) if str(item).strip()]
            if heading and items:
                deduped_items = _dedupe_text_list(items)
                if heading in section_index:
                    existing_items = section_index[heading]["items"]
                    existing_items.extend(item for item in deduped_items if item not in existing_items)
                else:
                    section = {"heading": heading, "items": deduped_items}
                    section_index[heading] = section
                    sections.append(section)
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

    sections = _dedupe_summary_sections(sections)

    summary = _format_detailed_summary_text(title, sections)
    return summary, title, sections


def _dedupe_summary_sections(sections: list[dict]) -> list[dict]:
    deduped_sections: list[dict] = []
    section_index: dict[str, dict] = {}

    for section in sections:
        heading = str(section.get("heading", "")).strip()
        if not heading:
            continue

        items = _dedupe_text_list([str(item).strip() for item in section.get("items", []) if str(item).strip()])
        if heading in section_index:
            existing_items = section_index[heading]["items"]
            existing_items.extend(item for item in items if item not in existing_items)
            continue

        deduped_section = {"heading": heading, "items": items}
        section_index[heading] = deduped_section
        deduped_sections.append(deduped_section)

    return deduped_sections


def _dedupe_text_list(items: list[str]) -> list[str]:
    deduped: list[str] = []
    seen = set()
    for item in items:
        normalized = _normalize_text(item)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(item)
    return deduped


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().lower()


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
    db: Session,
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
    docs, references = await _retrieve_context(
        queries=["Provide a high-yield summary of these study notes"],
        user_id=user_id,
        chat_id=chat_id,
        n_results=max(n_results, 8),
    )

    if not docs:
        raise ValueError("No uploaded notes found in this chat")
    
    context = "\n\n".join(docs)
    
    # Step 2: Generate flashcards using LLM
    consume_user_tokens(db, user_id, estimate_token_cost(context, max_tokens=max_tokens))
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

    cleaned_flashcards = _dedupe_flashcards(cleaned_flashcards)

    # Attach references
    for card in cleaned_flashcards:
        card["references"] = references

    return cleaned_flashcards, references


def _dedupe_flashcards(flashcards: list[dict]) -> list[dict]:
    deduped: list[dict] = []
    seen = set()

    for card in flashcards:
        topic = str(card.get("topic", "")).strip()
        summary = str(card.get("summary", "")).strip()
        explanation = str(card.get("explanation", "")).strip()
        key = (_normalize_text(topic), _normalize_text(summary))

        if not topic or not summary or not explanation or key in seen:
            continue

        seen.add(key)
        deduped.append({
            "topic": topic,
            "summary": summary,
            "explanation": explanation,
        })

    return deduped


async def generate_quiz(
    db: Session,
    user_id: int,
    chat_id: int,
    num_questions: int = 5,
    max_tokens: int = 1500,
) -> tuple[list[dict], list[dict]]:
    """
    Generate multiple-choice quiz questions from all uploaded notes in a chat.

    Args:
        user_id: ID of the user (for access control)
        chat_id: ID of the chat (for context filtering)
        num_questions: Number of MCQ questions to generate
        max_tokens: Max tokens for LLM output

    Returns:
        Tuple of (questions, references) where:
        - questions: List of dicts with question, options, correct_index, explanation
        - references: List of unique document references used

    Raises:
        ValueError: If no content found or parsing fails
    """
    docs, references = await _retrieve_context(
        queries=[BROAD_FALLBACK_QUERY],
        user_id=user_id,
        chat_id=chat_id,
        n_results=max(num_questions, 8),
    )

    if not docs:
        raise ValueError("No uploaded notes found in this chat")

    context = "\n\n".join(docs)

    consume_user_tokens(db, user_id, estimate_token_cost(context, max_tokens=max_tokens))
    quiz_output = await generate_quiz_llm(context, num_questions=num_questions, max_tokens=max_tokens)

    questions = parse_quiz_marker_output(quiz_output)
    if not questions:
        questions = parse_quiz_json_fallback(quiz_output)

    if not questions:
        raise ValueError(
            "Failed to parse quiz questions from model output. "
            f"Response preview: {quiz_output[:400]}..."
        )

    questions = _dedupe_quiz_questions(questions)[:num_questions]

    for question in questions:
        question["references"] = references

    return questions, references


def _dedupe_quiz_questions(questions: list[dict]) -> list[dict]:
    deduped: list[dict] = []
    seen = set()

    for item in questions:
        question = str(item.get("question", "")).strip()
        options = item.get("options", [])
        explanation = str(item.get("explanation", "")).strip()
        correct_index = item.get("correct_index")
        key = _normalize_text(question)

        if (
            not question
            or not isinstance(options, list)
            or len(options) != 4
            or not all(str(opt).strip() for opt in options)
            or not isinstance(correct_index, int)
            or not (0 <= correct_index <= 3)
            or key in seen
        ):
            continue

        seen.add(key)
        deduped.append({
            "question": question,
            "options": [str(opt).strip() for opt in options],
            "correct_index": correct_index,
            "explanation": explanation,
        })

    return deduped
