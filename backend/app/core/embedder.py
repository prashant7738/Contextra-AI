from sentence_transformers import SentenceTransformer

_model: SentenceTransformer | None = None
_MODEL_NAME = "BAAI/bge-small-en-v1.5"


def get_embedder() -> SentenceTransformer:
    global _model
    if _model is None:
        # CPU-only mode to avoid CUDA kernel compatibility issues
        # To enable GPU: install correct CUDA toolkit version matching your GPU, then set device="cuda"
        _model = SentenceTransformer(_MODEL_NAME, device="cpu")
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_embedder()
    embeddings = model.encode(texts, normalize_embeddings=True, batch_size=64)
    return embeddings.tolist()
