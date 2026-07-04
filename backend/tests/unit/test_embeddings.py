import logging

import httpx

from app.core import embeddings


def test_embed_huggingface_logs_diagnostics_and_falls_back_on_client_failure(monkeypatch, caplog):
    monkeypatch.setattr(embeddings.settings, "embedding_provider", "huggingface")
    monkeypatch.setattr(embeddings.settings, "hf_token", "hf_test_token")
    monkeypatch.setattr(embeddings, "_embed_local", lambda texts: [[9.0, 8.0, 7.0]])

    caplog.set_level(logging.INFO)

    class FailingInferenceClient:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def feature_extraction(self, *args, **kwargs):
            request = httpx.Request("POST", "https://router.huggingface.co/v1")
            raise httpx.ConnectError("No address associated with hostname", request=request)

    monkeypatch.setattr(embeddings, "InferenceClient", FailingInferenceClient)

    assert embeddings._embed_huggingface(["hello world"]) == [[9.0, 8.0, 7.0]]
    assert "provider=huggingface" in caplog.text
    assert "api_url=https://api-inference.huggingface.co/pipeline/feature-extraction/BAAI/bge-small-en-v1.5" in caplog.text
    assert "hostname=api-inference.huggingface.co" in caplog.text