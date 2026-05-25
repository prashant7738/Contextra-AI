from app.core.chunker import chunk_document
from app.core.embedder import embed_texts
from app.repositories.vector_repository import store_embeddings


def ingest_text(pages_data: list[dict], chunk_size: int = 100, user_id: int = None, document_id: int = None) -> int:
    """
    Ingest document pages, chunk them, embed them, and store in vector DB.
    
    Args:
        pages_data: List of dicts with page, text, and filename
        chunk_size: Size of chunks in words
        user_id: ID of the user uploading (stored in metadata)
        document_id: ID of the document (stored in metadata)
    
    Returns:
        Number of chunks created
    """
    chunks = chunk_document(pages_data, chunk_size=chunk_size)
    
    # Extract just text for embedding
    chunk_texts = [chunk["text"] for chunk in chunks]
    embeddings = embed_texts(chunk_texts)
    
    # Pass full chunks with user/doc ID for metadata storage
    store_embeddings(chunks, embeddings, user_id=user_id, document_id=document_id)
    return len(chunks)