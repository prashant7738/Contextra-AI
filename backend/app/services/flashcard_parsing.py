from __future__ import annotations

import json
import re


_BLOCK_START = re.compile(r"<<<FLASHCARD>>>", re.IGNORECASE)
_BLOCK_END = re.compile(r"<<<END>>>", re.IGNORECASE)
_FIELD_PATTERN = re.compile(
    r"(?im)^\s*(topic|summary|explanation)\s*[:\-]\s*(.*?)(?=^\s*(?:topic|summary|explanation)\s*[:\-]|\Z)",
    re.DOTALL | re.MULTILINE,
)


def parse_flashcard_marker_output(output: str) -> list[dict]:
    """
    Parse flashcards from marker output and tolerate missing end markers.
    """
    parsed: list[dict] = []
    chunks = _split_flashcard_chunks(output)

    for chunk in chunks:
        fields = _extract_fields(chunk)
        topic = fields.get("topic", "").strip()
        summary = fields.get("summary", "").strip()
        explanation = fields.get("explanation", "").strip()
        if topic and summary and explanation:
            parsed.append(
                {
                    "topic": topic,
                    "summary": summary,
                    "explanation": explanation,
                }
            )

    return parsed


def parse_flashcard_json_fallback(output: str) -> list[dict]:
    """
    Parse legacy JSON output if the model ignores the marker format.
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

        flashcards = parsed.get("flashcards", [])
        if not isinstance(flashcards, list):
            return []

        cleaned: list[dict] = []
        for card in flashcards:
            if not isinstance(card, dict):
                continue
            topic = str(card.get("topic", "")).strip()
            summary = str(card.get("summary", "")).strip()
            explanation = str(card.get("explanation", "")).strip()
            if topic and summary and explanation:
                cleaned.append(
                    {
                        "topic": topic,
                        "summary": summary,
                        "explanation": explanation,
                    }
                )
        return cleaned
    except Exception:
        return []


def _split_flashcard_chunks(output: str) -> list[str]:
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
