import asyncio

from app.services import retrieval_service
from app.services.quiz_service import grade_quiz_answers


def test_generate_quiz_retrieves_context_debits_tokens_and_parses_questions(monkeypatch):
    captured = {"queries": [], "context": None, "num_questions": None, "consumed": False}

    def fake_embed_texts(texts):
        query = texts[0]
        captured["queries"].append(query)
        return [[query]]

    def fake_query_similar(query_embedding, n_results, user_id, chat_id):
        query = query_embedding[0]
        if query == retrieval_service.BROAD_FALLBACK_QUERY:
            return {
                "documents": [[
                    "Binary search divides the sorted array in half each step.",
                    "Merge sort uses divide and conquer to split and combine arrays.",
                ]],
                "metadatas": [[
                    {"filename": "algorithms.pdf", "page": 8, "document_id": 11},
                    {"filename": "algorithms.pdf", "page": 9, "document_id": 11},
                ]],
                "distances": [[0.21, 0.24]],
            }
        raise AssertionError(f"Unexpected query: {query}")

    async def fake_generate_quiz_llm(context, num_questions, max_tokens=1500):
        captured["context"] = context
        captured["num_questions"] = num_questions
        return """
<<<MCQ>>>
QUESTION: What is the time complexity of binary search?
A: O(n)
B: O(log n)
C: O(n^2)
D: O(1)
CORRECT: B
EXPLANATION: Binary search halves the search space each step.
<<<END>>>
"""

    def fake_consume_user_tokens(db, user_id, cost):
        captured["consumed"] = True

    monkeypatch.setattr(retrieval_service, "embed_texts", fake_embed_texts)
    monkeypatch.setattr(retrieval_service, "query_similar", fake_query_similar)
    monkeypatch.setattr(retrieval_service, "generate_quiz_llm", fake_generate_quiz_llm)
    monkeypatch.setattr(retrieval_service, "consume_user_tokens", fake_consume_user_tokens)

    questions, references = asyncio.run(
        retrieval_service.generate_quiz(db=None, user_id=1, chat_id=1, num_questions=1)
    )

    assert captured["consumed"] is True
    assert captured["num_questions"] == 1
    assert len(questions) == 1
    q = questions[0]
    assert q["question"] == "What is the time complexity of binary search?"
    assert q["correct_index"] == 1
    assert q["references"] == references
    assert {ref["page"] for ref in references} == {8, 9}


def test_generate_quiz_raises_when_no_context_found(monkeypatch):
    def fake_embed_texts(texts):
        return [[texts[0]]]

    def fake_query_similar(query_embedding, n_results, user_id, chat_id):
        return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

    monkeypatch.setattr(retrieval_service, "embed_texts", fake_embed_texts)
    monkeypatch.setattr(retrieval_service, "query_similar", fake_query_similar)

    try:
        asyncio.run(retrieval_service.generate_quiz(db=None, user_id=1, chat_id=1, num_questions=5))
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "No uploaded notes" in str(exc)


def test_grade_quiz_answers_computes_score_and_marks_correctness():
    questions = [
        {"question": "Q1", "options": ["a", "b", "c", "d"], "correct_index": 1, "explanation": "exp1", "references": []},
        {"question": "Q2", "options": ["a", "b", "c", "d"], "correct_index": 2, "explanation": "exp2", "references": []},
        {"question": "Q3", "options": ["a", "b", "c", "d"], "correct_index": 0, "explanation": "exp3", "references": []},
    ]
    answers = [1, 0, 0]  # correct, wrong, correct

    score, results = grade_quiz_answers(questions, answers)

    assert score == 2
    assert [r["is_correct"] for r in results] == [True, False, True]
    assert results[1]["selected_index"] == 0
    assert results[1]["correct_index"] == 2


def test_grade_quiz_answers_handles_unanswered_questions():
    questions = [
        {"question": "Q1", "options": ["a", "b", "c", "d"], "correct_index": 3, "explanation": "exp1", "references": []},
    ]
    answers = [-1]  # unanswered

    score, results = grade_quiz_answers(questions, answers)

    assert score == 0
    assert results[0]["is_correct"] is False
