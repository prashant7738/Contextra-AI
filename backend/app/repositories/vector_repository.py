from __future__ import annotations

import uuid
from typing import Any

import chromadb
from chromadb.api.models.Collection import Collection

from app.settings import settings


_client: Any = None
_collection: Collection | None = None


def _strip_nul_chars(value: str | None) -> str:
    if not value:
        return ""
    return value.replace("\x00", "")


def get_collection() -> Collection:
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        _collection = _client.get_or_create_collection(
            name=settings.chroma_collection_name
        )
    return _collection


def store_embeddings(chunks: list[dict], embeddings: list[list[float]], user_id: int = None, document_id: int = None, chat_id: int = None):
    """
    Store chunks with metadata in ChromaDB.
    
    chunks = [
        {"text": "...", "page": 1, "filename": "doc.pdf"},
        {"text": "...", "page": 2, "filename": "doc.pdf"}
    ]
    """
    collection = get_collection()
    ids = [str(uuid.uuid4()) for _ in chunks]
    
    # Extract text from chunks
    documents = [_strip_nul_chars(chunk.get("text")) for chunk in chunks]
    
    # Create metadata for each chunk
    metadatas = []
    for chunk in chunks:
        metadata = {
            "page": chunk.get("page", 0),
            "filename": _strip_nul_chars(chunk.get("filename", "unknown")) or "unknown"
        }
        if user_id is not None:
            metadata["user_id"] = user_id
        if document_id is not None:
            metadata["document_id"] = document_id
        if chat_id is not None:
            metadata["chat_id"] = chat_id
        metadatas.append(metadata)
    
    collection.add(documents=documents, embeddings=embeddings, ids=ids, metadatas=metadatas)


def query_similar(query_embedding: list[float], n_results: int = 3, user_id: int = None, chat_id: int = None):
    """Query similar chunks with optional user_id and chat_id filtering."""
    collection = get_collection()
    
    # Build where filter for metadata if user_id and chat_id are provided
    where_filter = None
    if user_id is not None and chat_id is not None:
        where_filter = {
            "$and": [
                {"user_id": {"$eq": user_id}},
                {"chat_id": {"$eq": chat_id}}
            ]
        }
    elif user_id is not None:
        where_filter = {"user_id": {"$eq": user_id}}
    elif chat_id is not None:
        where_filter = {"chat_id": {"$eq": chat_id}}
    
    if where_filter:
        results = collection.query(query_embeddings=[query_embedding], n_results=n_results, where=where_filter)
    else:
        results = collection.query(query_embeddings=[query_embedding], n_results=n_results)
    
    # results includes: ids, distances, documents, metadatas
    return results
