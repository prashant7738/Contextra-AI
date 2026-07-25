from __future__ import annotations

import json
import re


_BLOCK_START = re.compile(r"<<<MCQ>>>", re.IGNORECASE)
_BLOCK_END = re.compile(r"<<<END>>>", re.IGNORECASE)
_FIELD_PATTERN = re.compile(
    r"(?im)^\s*(question|a|b|c|d|correct|explanation)\s*[:\-]\s*(.*?)"
    r"(?=^\s*(?:question|a|b|c|d|correct|explanation)\s*[:\-]|\Z)",
    re.DOTALL | re.MULTILINE,
)
_LETTER_TO_INDEX = {"a": 0, "b": 1, "c": 2, "d": 3}


def parse_quiz_marker_output(output: str) -> list[dict]:
    """
    Parse MCQ questions from marker output and tolerate missing end markers.

    Each returned dict has: question, options (list[str] len 4),
    correct_index (0-3), explanation.
    """
    parsed: list[dict] = []
    chunks = _split_quiz_chunks(output)

    for chunk in chunks:
        fields = _extract_fields(chunk)
        question = fields.get("question", "").strip()
        options = [fields.get(letter, "").strip() for letter in ("a", "b", "c", "d")]
        correct_letter = fields.get("correct", "").strip().lower()
        # Tolerate outputs like "A) text" or "Correct: A - because..."
        correct_letter_match = re.match(r"[abcd]", correct_letter)
        explanation = fields.get("explanation", "").strip()

        if not question or not all(options) or not correct_letter_match:
            continue

        parsed.append(
            {
                "question": question,
                "options": options,
                "correct_index": _LETTER_TO_INDEX[correct_letter_match.group(0)],
                "explanation": explanation,
            }
        )

    return parsed


def parse_quiz_json_fallback(output: str) -> list[dict]:
    """
    Parse legacy JSON output if the model ignores the marker format.

    Expected shape: {"questions": [{"question", "options": [...], "correct_index", "explanation"}]}
    """
    try:
        json_start = output.find("{")
        json_end = output.rfind("}") + 1
        if json_start < 0 or json_end <= json_start:
            return []

        json_str = output[json_start:json_end].strip()
        try:
            parsed = json.loads(json_str)
        except json.JSONDecodeError:
            json_str = _fix_json_issues(json_str)
            parsed = json.loads(json_str)

        questions = parsed.get("questions", [])
        if not isinstance(questions, list):
            return []

        cleaned: list[dict] = []
        for item in questions:
            if not isinstance(item, dict):
                continue
            question = str(item.get("question", "")).strip()
            options = item.get("options", [])
            if not isinstance(options, list) or len(options) != 4:
                continue
            options = [str(opt).strip() for opt in options]
            correct_index = item.get("correct_index")
            explanation = str(item.get("explanation", "")).strip()
            if (
                question
                and all(options)
                and isinstance(correct_index, int)
                and 0 <= correct_index <= 3
            ):
                cleaned.append(
                    {
                        "question": question,
                        "options": options,
                        "correct_index": correct_index,
                        "explanation": explanation,
                    }
                )
        return cleaned
    except Exception:
        return []


def _split_quiz_chunks(output: str) -> list[str]:
    matches = list(_BLOCK_START.finditer(output))
    if not matches:
        return []

    chunks: list[str] = []
    for index, match in enumerate(matches):
        start = match.end()
        next_start = matches[index + 1].start() if index + 1 < len(matches) else len(output)
        end_marker = _BLOCK_END.search(output, start, next_start)
        end = end_marker.start() if end_marker else next_start
        chunk = output[start:end].strip()
        if chunk:
            chunks.append(chunk)
    return chunks


def _extract_fields(chunk: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for match in _FIELD_PATTERN.finditer(chunk):
        key = match.group(1).lower()
        value = match.group(2).strip()
        if value:
            fields[key] = value
    return fields


def _fix_json_issues(json_str: str) -> str:
    json_str = re.sub(r",(\s*[}\]])", r"\1", json_str)
    json_str = re.sub(r"(\})\s*(\{)", r"\1,\2", json_str)
    json_str = "".join(char for char in json_str if ord(char) >= 32 or char in "\n\r\t")
    return json_str
