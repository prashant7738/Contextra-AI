from app.services.quiz_parsing import parse_quiz_json_fallback, parse_quiz_marker_output


def test_parse_quiz_marker_output_parses_single_block():
    output = """
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
    questions = parse_quiz_marker_output(output)

    assert len(questions) == 1
    q = questions[0]
    assert q["question"] == "What is the time complexity of binary search?"
    assert q["options"] == ["O(n)", "O(log n)", "O(n^2)", "O(1)"]
    assert q["correct_index"] == 1
    assert q["explanation"] == "Binary search halves the search space each step."


def test_parse_quiz_marker_output_parses_multiple_blocks_and_tolerates_missing_end_marker():
    output = """
<<<MCQ>>>
QUESTION: What does LIFO stand for?
A: Last In First Out
B: Last In Final Out
C: Least In First Out
D: Last Index First Out
CORRECT: A
EXPLANATION: A stack follows LIFO order.
<<<MCQ>>>
QUESTION: What does FIFO stand for?
A: First In Final Out
B: First Index First Out
C: First In First Out
D: Final In First Out
CORRECT: C
EXPLANATION: A queue follows FIFO order.
<<<END>>>
"""
    questions = parse_quiz_marker_output(output)

    assert len(questions) == 2
    assert questions[0]["correct_index"] == 0
    assert questions[1]["correct_index"] == 2


def test_parse_quiz_marker_output_skips_incomplete_blocks():
    output = """
<<<MCQ>>>
QUESTION: Missing options block
A: only one option
CORRECT: A
EXPLANATION: incomplete
<<<END>>>
"""
    questions = parse_quiz_marker_output(output)
    assert questions == []


def test_parse_quiz_json_fallback_parses_valid_json():
    output = """
    {
      "questions": [
        {
          "question": "What is 2+2?",
          "options": ["3", "4", "5", "6"],
          "correct_index": 1,
          "explanation": "Basic arithmetic."
        }
      ]
    }
    """
    questions = parse_quiz_json_fallback(output)

    assert len(questions) == 1
    assert questions[0]["question"] == "What is 2+2?"
    assert questions[0]["correct_index"] == 1


def test_parse_quiz_json_fallback_returns_empty_on_invalid_json():
    assert parse_quiz_json_fallback("not json at all") == []


def test_parse_quiz_json_fallback_skips_entries_missing_four_options():
    output = """
    {
      "questions": [
        {"question": "Bad question", "options": ["a", "b"], "correct_index": 0, "explanation": "x"}
      ]
    }
    """
    assert parse_quiz_json_fallback(output) == []
