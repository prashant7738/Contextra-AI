import asyncio
import logging

import openai
from openai import OpenAI

from app.core.openai_client import get_openai_client, is_unbilled_error
from app.services import spend_budget_service as budget

logger = logging.getLogger(__name__)

OPENAI_MODEL = "gpt-6-luna"
REASONING_EFFORT = "low"

# Optional params the model rejected with a 400; skipped on later calls.
_unsupported_params: set[str] = set()


def _create_completion(client: OpenAI, prompt: str, max_tokens: int, temperature: float):
    optional = {"temperature": temperature, "reasoning_effort": REASONING_EFFORT}
    while True:
        kwargs = {k: v for k, v in optional.items() if k not in _unsupported_params}
        try:
            return client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=max_tokens,
                **kwargs,
            )
        except openai.BadRequestError as exc:
            rejected = next((name for name in kwargs if name in str(exc)), None)
            if rejected is None:
                raise
            logger.warning("%s rejected parameter %s; retrying without it", OPENAI_MODEL, rejected)
            _unsupported_params.add(rejected)


def _generate_text(prompt: str, max_tokens: int, temperature: float) -> str:
    """Call gpt-6-luna, charging the global daily budget with the real usage."""
    reserved = budget.reserve(budget.llm_worst_case_micro(prompt, max_tokens))
    try:
        response = _create_completion(get_openai_client(), prompt, max_tokens, temperature)
    except Exception as exc:
        if is_unbilled_error(exc):
            budget.settle(reserved, 0)
        raise

    usage = response.usage
    if usage is not None:
        details = getattr(usage, "prompt_tokens_details", None)
        cached = getattr(details, "cached_tokens", 0) or 0
        budget.settle(reserved, budget.llm_cost_micro(usage.prompt_tokens, cached, usage.completion_tokens))

    text = response.choices[0].message.content
    if not text:
        raise RuntimeError("The model returned an empty response")
    return text


def _build_chat_prompt(context: str, question: str) -> str:
    return f"""
You are a helpful assistant.
Use the following context to answer the question by synthesizing all relevant excerpts.
Do not say you don't know just because the wording is different or the answer must be combined from multiple chunks.
Only say you don't know if the context truly does not support an answer.
Prefer a direct answer first, then brief supporting detail if helpful.

Context:
{context}

Question: {question}
"""


def _ask_llm_sync(context: str, question: str, max_tokens: int = 800) -> str:
    """Synchronous LLM call - runs in thread pool."""
    prompt = _build_chat_prompt(context, question)
    return _generate_text(prompt, max_tokens, temperature=0.1)


async def ask_llm(context: str, question: str, max_tokens: int = 800) -> str:
    """Async wrapper for LLM call - runs in thread pool to avoid blocking."""
    return await asyncio.to_thread(_ask_llm_sync, context, question, max_tokens)


def _build_detailed_summary_prompt(context: str, topic_name: str) -> str:
    return f"""
You are an expert study assistant.
Create an 80/20 summary from the provided notes.

Rules:
- Return only the highest-yield 20% concepts that cover about 80% of the learning value.
- Make the Core Concepts section the longest and most detailed part of the answer.
- Core Concepts should usually contain 5 to 8 items, and each item should be 2 to 4 sentences long.
- For each Core Concepts item, explain what it is, why it matters, and include a simple example or analogy when helpful.
- Keep Must Remember shorter and sharper, usually 3 to 5 concise items.
- Keep Quick Revision Checklist brief and practical, usually 4 to 6 short checklist-style items.
- Do not add information that is not present in the context.
- If context is insufficient, explicitly mention the limitation.
- Return valid JSON only.
- Do not use markdown, code fences, or extra commentary.

Topic requested: {topic_name}

Output format:
{{
  "title": "Short summary title",
  "sections": [
    {{
      "heading": "Core Concepts",
      "items": ["point 1", "point 2"]
    }},
    {{
      "heading": "Must Remember",
      "items": ["point 1", "point 2"]
    }},
    {{
      "heading": "Quick Revision Checklist",
      "items": ["point 1", "point 2"]
    }}
  ]
}}

Context:
{context}
"""


def _ask_detailed_summary_llm_sync(context: str, topic_name: str, max_tokens: int = 700) -> str:
    """Synchronous detailed summary - runs in thread pool."""
    prompt = _build_detailed_summary_prompt(context, topic_name)
    return _generate_text(prompt, max_tokens, temperature=0.1)


async def ask_detailed_summary_llm(context: str, topic_name: str, max_tokens: int = 700) -> str:
    """Async wrapper for detailed summary - runs in thread pool to avoid blocking."""
    return await asyncio.to_thread(_ask_detailed_summary_llm_sync, context, topic_name, max_tokens)


def _build_flashcards_prompt(context: str) -> str:
    return f"""Generate learning flashcards from the content below.

Output constraints (strict):
- Do NOT return JSON.
- Return only repeated blocks in this exact structure:

<<<FLASHCARD>>>
TOPIC: <topic name>
SUMMARY: <one short line, max 15 words>
EXPLANATION: <2-4 sentence detailed explanation>
<<<END>>>

Rules:
1. Cover all major topics and subtopics from the content.
2. Important/large topics should have more flashcards than minor topics.
3. Every block must contain TOPIC, SUMMARY, and EXPLANATION.
4. No extra text outside the blocks.

Content:
{context}
"""


def _generate_flashcards_llm_sync(context: str, max_tokens: int = 1000) -> str:
    """Synchronous flashcard generation - runs in thread pool."""
    prompt = _build_flashcards_prompt(context)
    return _generate_text(prompt, max_tokens, temperature=0.2)


async def generate_flashcards_llm(context: str, max_tokens: int = 1000) -> str:
    """Async wrapper for flashcard generation - runs in thread pool to avoid blocking."""
    return await asyncio.to_thread(_generate_flashcards_llm_sync, context, max_tokens)


def _build_quiz_prompt(context: str, num_questions: int) -> str:
    return f"""Generate exactly {num_questions} multiple-choice quiz questions from the content below.

Output constraints (strict):
- Do NOT return JSON.
- Return only repeated blocks in this exact structure:

<<<MCQ>>>
QUESTION: <question text>
A: <option text>
B: <option text>
C: <option text>
D: <option text>
CORRECT: <A|B|C|D>
EXPLANATION: <1-2 sentence explanation of why the correct answer is right>
<<<END>>>

Rules:
1. Produce exactly {num_questions} blocks, no more, no fewer.
2. Each question must have exactly 4 distinct, plausible options.
3. Only one option is correct; CORRECT must be a single letter A, B, C, or D.
4. Cover a range of topics/subtopics from the content, avoid duplicate questions.
5. No extra text outside the blocks.

Content:
{context}
"""


def _generate_quiz_llm_sync(context: str, num_questions: int, max_tokens: int = 1500) -> str:
    """Synchronous MCQ quiz generation - runs in thread pool."""
    prompt = _build_quiz_prompt(context, num_questions)
    return _generate_text(prompt, max_tokens, temperature=0.2)


async def generate_quiz_llm(context: str, num_questions: int, max_tokens: int = 1500) -> str:
    """Async wrapper for quiz generation - runs in thread pool to avoid blocking."""
    return await asyncio.to_thread(_generate_quiz_llm_sync, context, num_questions, max_tokens)
