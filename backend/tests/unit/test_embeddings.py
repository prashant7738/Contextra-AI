from types import SimpleNamespace

import pytest

from app.core import embeddings


def _response(vectors, total_tokens):
    data = [SimpleNamespace(index=i, embedding=v) for i, v in enumerate(vectors)]
    return SimpleNamespace(data=list(reversed(data)), usage=SimpleNamespace(total_tokens=total_tokens))


def _client(create):
    return SimpleNamespace(embeddings=SimpleNamespace(create=create))


def test_embed_texts_uses_small_model_with_384_dims_and_settles_usage(monkeypatch):
    captured = {}
    ledger = {}

    def create(**kwargs):
        captured.update(kwargs)
        return _response([[1.0], [2.0]], total_tokens=1000)

    monkeypatch.setattr(embeddings, "get_openai_client", lambda: _client(create))
    monkeypatch.setattr(embeddings.budget, "reserve", lambda micro: micro)
    monkeypatch.setattr(embeddings.budget, "settle", lambda reserved, actual: ledger.update(settled=(reserved, actual)))

    result = embeddings.embed_texts(["a", "b"])

    assert captured["model"] == "text-embedding-3-small"
    assert captured["dimensions"] == 384
    # Results come back in input order even if the API returns them shuffled.
    assert result == [[1.0], [2.0]]
    assert ledger["settled"][1] == 20  # 1000 tokens at $0.02 / 1M = 20 micro-USD


def test_embed_texts_batches_large_inputs(monkeypatch):
    batch_sizes = []

    def create(**kwargs):
        batch_sizes.append(len(kwargs["input"]))
        return _response([[0.0]] * len(kwargs["input"]), total_tokens=1)

    monkeypatch.setattr(embeddings, "get_openai_client", lambda: _client(create))
    monkeypatch.setattr(embeddings.budget, "reserve", lambda micro: micro)
    monkeypatch.setattr(embeddings.budget, "settle", lambda reserved, actual: None)

    embeddings.embed_texts(["x"] * 600)

    assert batch_sizes == [256, 256, 88]


def test_embed_texts_does_not_call_openai_when_budget_is_exhausted(monkeypatch):
    from fastapi import HTTPException

    def reserve(micro):
        raise HTTPException(status_code=429, detail="Daily AI budget reached.")

    monkeypatch.setattr(embeddings.budget, "reserve", reserve)
    monkeypatch.setattr(
        embeddings, "get_openai_client", lambda: pytest.fail("OpenAI must not be called over budget")
    )

    with pytest.raises(HTTPException) as exc_info:
        embeddings.embed_texts(["hello"])

    assert exc_info.value.status_code == 429
