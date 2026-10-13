import logging

from app.core.openai_client import get_openai_client, is_unbilled_error
from app.services import spend_budget_service as budget

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "text-embedding-3-small"
# Matches the Vector(384) column; text-embedding-3 models can return shortened vectors.
EMBEDDING_DIM = 384
_BATCH_SIZE = 256


def embed_texts(texts: list[str]) -> list[list[float]]:
    vectors: list[list[float]] = []
    for start in range(0, len(texts), _BATCH_SIZE):
        vectors.extend(_embed_batch(texts[start : start + _BATCH_SIZE]))
    return vectors


def _embed_batch(batch: list[str]) -> list[list[float]]:
    reserved = budget.reserve(budget.embedding_cost_micro(budget.estimate_tokens(*batch)))
    try:
        response = get_openai_client().embeddings.create(
            model=EMBEDDING_MODEL,
            input=batch,
            dimensions=EMBEDDING_DIM,
        )
    except Exception as exc:
        if is_unbilled_error(exc):
            budget.settle(reserved, 0)
        raise

    usage = getattr(response, "usage", None)
    if usage is not None:
        budget.settle(reserved, budget.embedding_cost_micro(usage.total_tokens))

    logger.info("OpenAI embedding: %d texts", len(batch))
    return [item.embedding for item in sorted(response.data, key=lambda item: item.index)]
