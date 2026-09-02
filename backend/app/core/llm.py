import asyncio
import logging

from google import genai
from google.genai import types
from huggingface_hub import InferenceClient

from app.settings import settings

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-3.7-flash"

_gemini_client: genai.Client | None = None
_fallback_client: InferenceClient | None = None


def get_gemini_client() -> genai.Client:
    """Primary LLM client; reads GEMINI_API_KEY/GOOGLE_API_KEY from the environment."""
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client()
    return _gemini_client


def get_fallback_llm() -> InferenceClient:
    global _fallback_client
    if _fallback_client is None:
        if not settings.hf_token:
            raise RuntimeError("Hugging Face API token not set. Set `HF_TOKEN` in environment or .env as `hf_token`.")
        _fallback_client = InferenceClient(
            model="meta-llama/Llama-3.1-8B-Instruct",
            api_key=settings.hf_token,
        )
    return _fallback_client


def _generate_text(prompt: str, max_tokens: int, temperature: float) -> str:
    """Try Gemini first; on any failure, fall back to the HuggingFace client."""
    try:
        client = get_gemini_client()
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
            ),
        )
        return response.text
    except Exception:
        logger.warning("Gemini call failed, falling back to HuggingFace", exc_info=True)
        client = get_fallback_llm()
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content


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
