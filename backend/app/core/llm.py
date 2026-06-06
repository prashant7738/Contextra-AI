from huggingface_hub import InferenceClient

from app.settings import settings


_chat_client: InferenceClient | None = None


def get_llm() -> InferenceClient:
    global _chat_client
    if _chat_client is None:
        if not settings.hf_token:
            raise RuntimeError("Hugging Face API token not set. Set `HF_TOKEN` in environment or .env as `hf_token`.")
        _chat_client = InferenceClient(
            model="meta-llama/Llama-3.1-8B-Instruct",
            api_key=settings.hf_token,
        )
    return _chat_client





def ask_llm(context: str, question: str, max_tokens: int = 500) -> str:
    client = get_llm()
    prompt = f"""
You are a helpful assistant. Use the following context to answer the question.
If you don't know the answer, say you don't know.

Context:
{context}

Question: {question}
"""
    response = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0.1,
    )
    return response.choices[0].message.content





def ask_detailed_summary_llm(context: str, topic_name: str, max_tokens: int = 700) -> str:
    client = get_llm()
    prompt = f"""
You are an expert study assistant.
Create an 80/20 summary from the provided notes.

Rules:
- Return only the highest-yield 20% concepts that cover about 80% of the learning value.
- Keep it concise and easy for students to revise quickly.
- Do not add information that is not present in the context.
- If context is insufficient, explicitly mention the limitation.

Topic requested: {topic_name}

Output format:
1) Core Concepts (short bullets)
2) Must Remember (high-yield points)
3) Quick Revision Checklist

Context:
{context}
"""
    response = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0.1,
    )
    return response.choices[0].message.content


def generate_flashcards_llm(context: str, max_tokens: int = 1000) -> str:
    """
    Generate flashcards from context. Returns JSON with topics and their flashcard data.
    """
    client = get_llm()
    prompt = f"""Generate flashcards for learning. Return ONLY valid JSON, nothing else.

CRITICAL: Your entire response must be ONLY the JSON object, starting with {{ and ending with }}. No text before or after.

Rules:
1. Identify ALL major topics and subtopics
2. Important/large topics: 8-12 flashcards
3. Medium topics: 4-7 flashcards
4. Small topics: 2-3 flashcards

Each flashcard:
- topic: exact topic name (string)
- summary: ONE short sentence, max 15 words (string)
- explanation: detailed explanation, 2-3 sentences (string)

JSON format (ONLY this, nothing else):
{{
  "flashcards": [
    {{
      "topic": "topic name",
      "summary": "short summary",
      "explanation": "detailed explanation"
    }}
  ]
}}

Content to extract from:
{context}"""
    response = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0.2,
    )
    return response.choices[0].message.content
