import logging
from typing import Optional

import httpx

from app.settings import settings

logger = logging.getLogger(__name__)


_EMBEDDING_DIM = 384


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

    api_url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/BAAI/bge-small-en-v1.5"
    headers = {"Authorization": f"Bearer {settings.hf_token}"}
    body = {"inputs": texts, "options": {"wait_for_model": True}}

    resp = httpx.post(api_url, headers=headers, json=body, timeout=120)
    resp.raise_for_status()
    data = resp.json()

    if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
        embeddings = data
    else:
        logger.error(f"Unexpected HF embedding response shape: {type(data)}")
        raise ValueError("Unexpected embedding response from HuggingFace API")

    logger.info(f"HuggingFace embedding: {len(texts)} texts → {len(embeddings)} embeddings")
    return embeddings


def _embed_local(texts: list[str]) -> list[list[float]]:
    from app.core.embedder import embed_texts as local_embed
    return local_embed(texts)
