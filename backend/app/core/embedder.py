from huggingface_hub import InferenceClient

from app.settings import settings


_client: InferenceClient | None = None


def get_embedder() -> InferenceClient:
    global _client
    if _client is None:
        if not settings.hf_token:
            raise RuntimeError("Hugging Face API token not set. Set `HF_TOKEN` in environment or .env as `hf_token`.")
        _client = InferenceClient(provider="hf-inference", api_key=settings.hf_token)
    return _client


def embed_texts(texts: list[str]) -> list[list[float]]:
    client = get_embedder()
    result = client.feature_extraction(texts, model="BAAI/bge-base-en-v1.5")
    return result if isinstance(result, list) else result.tolist()
