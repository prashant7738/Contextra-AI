import logging
from urllib.parse import urlparse

import httpx
from huggingface_hub import InferenceClient

from app.settings import settings

logger = logging.getLogger(__name__)


_EMBEDDING_DIM = 384
_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
_LEGACY_HF_API_URL = "https://api-inference.huggingface.co/pipeline/feature-extraction/BAAI/bge-small-en-v1.5"


def embed_texts(texts: list[str]) -> list[list[float]]:
    provider = settings.embedding_provider or "local"
    if provider == "openai":
        return _embed_openai(texts)
    elif provider == "huggingface":
        return _embed_huggingface(texts)
    else:
        return _embed_local(texts)


def _embed_openai(texts: list[str]) -> list[list[float]]:
    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY not set, falling back to local embedding")
        return _embed_local(texts)

    url = "https://api.openai.com/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": "text-embedding-3-small",
        "input": texts,
        "dimensions": _EMBEDDING_DIM,
    }
    resp = httpx.post(url, headers=headers, json=body, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    embeddings = [item["embedding"] for item in data["data"]]
    logger.info(f"OpenAI embedding: {len(texts)} texts → {len(embeddings)} embeddings")
    return embeddings


def _embed_huggingface(texts: list[str]) -> list[list[float]]:
    if not settings.hf_token:
        logger.warning("HF_TOKEN not set, falling back to local embedding")
        return _embed_local(texts)

    hostname = urlparse(_LEGACY_HF_API_URL).hostname
    logger.info(
        "HuggingFace embedding config: provider=%s api_url=%s hostname=%s",
        settings.embedding_provider,
        _LEGACY_HF_API_URL,
        hostname,
    )

    try:
        client = InferenceClient(model=_EMBEDDING_MODEL, api_key=settings.hf_token)
        embeddings = client.feature_extraction(texts, normalize=True, model=_EMBEDDING_MODEL)
    except (httpx.HTTPError, OSError, ValueError) as exc:
        logger.warning(
            "Hugging Face embeddings unavailable (%s); falling back to local embeddings",
            exc,
        )
        return _embed_local(texts)

    if hasattr(embeddings, "tolist"):
        embeddings = embeddings.tolist()

    if not isinstance(embeddings, list) or len(embeddings) == 0 or not isinstance(embeddings[0], list):
        logger.warning("Unexpected HF embedding response shape: %s; falling back to local embeddings", type(embeddings))
        return _embed_local(texts)

    logger.info(f"HuggingFace embedding: {len(texts)} texts → {len(embeddings)} embeddings")
    return embeddings


def _embed_local(texts: list[str]) -> list[list[float]]:
    from app.core.embedder import embed_texts as local_embed
    return local_embed(texts)
