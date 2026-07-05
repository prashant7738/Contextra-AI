import asyncio

from app.services import retrieval_service


def test_answer_query_prefers_filename_specific_context(monkeypatch):
    captured = {"queries": [], "context": None}

    def fake_embed_texts(texts):
        captured["queries"].append(texts[0])
        return [[texts[0]]]

    def fake_query_similar(query_embedding, n_results, user_id, chat_id):
        query = query_embedding[0].lower()
        if query in {'file1', 'file1.pdf'}:
            return {
                'documents': [['File1 explains binary search clearly.']],
                'metadatas': [[{'filename': 'file1.pdf', 'page': 1, 'document_id': 1}]],
                'distances': [[0.1]],
            }
        return {
            'documents': [['General notes about other algorithms.']],
            'metadatas': [[{'filename': 'file2.pdf', 'page': 2, 'document_id': 2}]],
            'distances': [[0.2]],
        }

    async def fake_ask_llm(context, question, max_tokens=800):
        captured['context'] = context
        return 'answer'

    monkeypatch.setattr(retrieval_service, 'embed_texts', fake_embed_texts)
    monkeypatch.setattr(retrieval_service, 'query_similar', fake_query_similar)
    monkeypatch.setattr(retrieval_service, 'ask_llm', fake_ask_llm)
    monkeypatch.setattr(retrieval_service, 'consume_user_tokens', lambda *args, **kwargs: None)

    answer, references = asyncio.run(
        retrieval_service.answer_query(
            db=None,
            question='tell me about file1',
            user_id=1,
            chat_id=1,
            chat_history=None,
        )
    )

    assert answer == 'answer'
    assert captured['context'] is not None
    assert 'File1 explains binary search clearly.' in captured['context']
    assert references[0]['filename'] == 'file1.pdf'
    assert any(q.lower() in {'file1', 'file1.pdf'} for q in captured['queries'])
