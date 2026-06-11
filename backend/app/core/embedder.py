from sentence_transformers import SentenceTransformer

_model: SentenceTransformer | None = None
_MODEL_NAME = "BAAI/bge-small-en-v1.5"


def _get_device() -> str:
    try:
        import torch
        return "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        return "cpu"


def get_embedder() -> SentenceTransformer:
    global _model
    if _model is None:
        device = _get_device()
        _model = SentenceTransformer(_MODEL_NAME, device=device)
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_embedder()
    embeddings = model.encode(texts, normalize_embeddings=True, batch_size=64)
    return embeddings.tolist()
