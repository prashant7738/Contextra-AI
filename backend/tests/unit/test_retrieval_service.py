import asyncio

from app.services import retrieval_service


def test_answer_query_merges_specific_and_broad_retrieval_context(monkeypatch):
    captured = {"queries": [], "context": None}

    def fake_embed_texts(texts):
        query = texts[0]
        captured["queries"].append(query)
        return [[query]]

    def fake_query_similar(query_embedding, n_results, user_id, chat_id):
        query = query_embedding[0]
        if query == "search algorithm":
            return {
                "documents": [["Minimax is a search algorithm used in adversarial games."]],
                "metadatas": [[{"filename": "algorithms.pdf", "page": 4, "document_id": 11}]],
                "distances": [[0.12]],
            }

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

    async def fake_ask_llm(context, question, max_tokens=800):
        captured["context"] = context
        return "answer"

    monkeypatch.setattr(retrieval_service, "embed_texts", fake_embed_texts)
    monkeypatch.setattr(retrieval_service, "query_similar", fake_query_similar)
    monkeypatch.setattr(retrieval_service, "ask_llm", fake_ask_llm)
    monkeypatch.setattr(retrieval_service, "consume_user_tokens", lambda *args, **kwargs: None)

    answer, references = asyncio.run(
        retrieval_service.answer_query(
            db=None,
            question="search algorithm",
            user_id=1,
            chat_id=1,
            chat_history=None,
        )
    )

    assert answer == "answer"
    assert captured["context"] is not None
    assert "Minimax is a search algorithm" in captured["context"]
    assert "Binary search divides the sorted array" in captured["context"]
    assert "Merge sort uses divide and conquer" in captured["context"]
    assert len(captured["queries"]) == 2
    assert {ref["page"] for ref in references} == {4, 8, 9}


def test_generate_detailed_summary_for_all_uses_broader_topic_coverage(monkeypatch):
    captured = {"queries": [], "context": None}

    def fake_embed_texts(texts):
        query = texts[0]
        captured["queries"].append(query)
        return [[query]]

    def fake_query_similar(query_embedding, n_results, user_id, chat_id):
        query = query_embedding[0]
        if query == retrieval_service.BROAD_FALLBACK_QUERY:
            return {
                "documents": [["Stacks follow LIFO while queues follow FIFO."]],
                "metadatas": [[{"filename": "data-structures.pdf", "page": 2, "document_id": 21}]],
                "distances": [[0.11]],
            }

        if query == "List all major topics and subtopics from these study notes":
            return {
                "documents": [["Hash tables give average O(1) lookup and insertion."]],
                "metadatas": [[{"filename": "data-structures.pdf", "page": 5, "document_id": 21}]],
                "distances": [[0.19]],
            }

        raise AssertionError(f"Unexpected query: {query}")

    async def fake_ask_detailed_summary_llm(context, topic_name, max_tokens=700):
        captured["context"] = context
        return '{"title":"Study guide","sections":[{"heading":"Core Concepts","items":["x"]}]}'

    monkeypatch.setattr(retrieval_service, "embed_texts", fake_embed_texts)
    monkeypatch.setattr(retrieval_service, "query_similar", fake_query_similar)
    monkeypatch.setattr(retrieval_service, "ask_detailed_summary_llm", fake_ask_detailed_summary_llm)
    monkeypatch.setattr(retrieval_service, "consume_user_tokens", lambda *args, **kwargs: None)

    summary, title, sections, references, chunks_used = asyncio.run(
        retrieval_service.generate_detailed_summary(
            db=None,
            topic_name="all",
            user_id=1,
            chat_id=1,
            n_results=5,
            max_tokens=700,
            pre_generated_answer=None,
        )
    )

    assert title == "Study guide"
    assert summary.startswith("Study guide")
    assert sections == [{"heading": "Core Concepts", "items": ["x"]}]
    assert captured["context"] is not None
    assert "Stacks follow LIFO" in captured["context"]
    assert "Hash tables give average O(1) lookup" in captured["context"]
    assert len(captured["queries"]) == 2
    assert chunks_used == 2
    assert {ref["page"] for ref in references} == {2, 5}


def test_parse_detailed_summary_output_deduplicates_repeated_items():
    output = '''
    {
      "title": "Algorithms",
      "sections": [
        {"heading": "Core Concepts", "items": ["Binary search divides the array", "Binary search divides the array", "Merge sort splits and merges"]},
        {"heading": "Core Concepts", "items": ["Merge sort splits and merges"]},
        {"heading": "Revision", "items": ["Binary search divides the array"]}
      ]
    }
    '''

    summary, title, sections = retrieval_service._parse_detailed_summary_output(output, "all")

    assert title == "Algorithms"
    assert sections == [
        {"heading": "Core Concepts", "items": ["Binary search divides the array", "Merge sort splits and merges"]},
        {"heading": "Revision", "items": ["Binary search divides the array"]},
    ]
    assert summary.count("Binary search divides the array") == 2


def test_generate_flashcards_deduplicates_duplicate_cards(monkeypatch):
    monkeypatch.setattr(retrieval_service, "embed_texts", lambda texts: [[texts[0]]])
    monkeypatch.setattr(
        retrieval_service,
        "query_similar",
        lambda query_embedding, n_results, user_id, chat_id: {
            "documents": [["Topic A details", "Topic B details"]],
            "metadatas": [[
                {"filename": "notes.pdf", "page": 1, "document_id": 1},
                {"filename": "notes.pdf", "page": 2, "document_id": 1},
            ]],
        },
    )
    async def fake_generate_flashcards_llm(*args, **kwargs):
        return '''
<<<FLASHCARD>>>
TOPIC: Binary Search
SUMMARY: Search halves the array
EXPLANATION: It compares the middle element.
<<<END>>>
<<<FLASHCARD>>>
TOPIC: Binary Search
SUMMARY: Search halves the array
EXPLANATION: It compares the middle element.
<<<END>>>
'''

    monkeypatch.setattr(retrieval_service, "generate_flashcards_llm", fake_generate_flashcards_llm)
    monkeypatch.setattr(retrieval_service, "consume_user_tokens", lambda *args, **kwargs: None)

    cards, references = asyncio.run(
        retrieval_service.generate_flashcards(
            db=None,
            user_id=1,
            chat_id=1,
            n_results=5,
            max_tokens=1000,
        )
    )

    assert len(cards) == 1
    assert cards[0]["topic"] == "Binary Search"
    assert len(references) == 2