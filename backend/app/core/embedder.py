from sentence_transformers import SentenceTransformer

_model: SentenceTransformer | None = None
_MODEL_NAME = "BAAI/bge-base-en-v1.5"


def get_embedder() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(_MODEL_NAME, device="cpu")
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_embedder()
    embeddings = model.encode(texts, normalize_embeddings=True)
    return embeddings.tolist()
