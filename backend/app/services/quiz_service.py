from __future__ import annotations


def grade_quiz_answers(questions: list[dict], answers: list[int]) -> tuple[int, list[dict]]:
    """
    Grade a list of submitted answers against stored quiz questions.

    Args:
        questions: List of dicts with question, options, correct_index, explanation, references
        answers: List of selected option indices (same length as questions; -1 = unanswered)

    Returns:
        Tuple of (score, results) where results is a list of dicts with
        question, options, selected_index, correct_index, is_correct, explanation, references.
    """
    score = 0
    results: list[dict] = []

    for question, selected_index in zip(questions, answers):
        correct_index = question.get("correct_index", -1)
        is_correct = selected_index == correct_index
        if is_correct:
            score += 1
        results.append(
            {
                "question": question.get("question", ""),
                "options": question.get("options", []),
                "selected_index": selected_index,
                "correct_index": correct_index,
                "is_correct": is_correct,
                "explanation": question.get("explanation", ""),
                "references": question.get("references", []),
            }
        )

    return score, results
