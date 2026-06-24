from __future__ import annotations

import uuid
from typing import Any
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from pgvector.sqlalchemy import Vector

from app.database import SessionLocal
from app.models.embedding import Embedding


def get_db() -> Session:
    return SessionLocal()


def store_embeddings(
    chunks: list[dict],
    embeddings: list[list[float]],
    user_id: int | None = None,
    document_id: int | None = None,
    chat_id: int | None = None,
) -> int:
    db = get_db()
    try:
        count = 0
        for chunk, embedding in zip(chunks, embeddings):
            emb = Embedding(
                id=uuid.uuid4(),
                user_id=user_id,
                document_id=document_id,
                chat_id=chat_id,
                content=chunk.get("text", ""),
                embedding=embedding,
                chunk_metadata={
                    "page": chunk.get("page", 0),
                    "filename": chunk.get("filename", "unknown"),
                },
            )
            db.add(emb)
            count += 1
        db.commit()
        return count
    finally:
        db.close()


def query_similar(
    query_embedding: list[float],
    n_results: int = 3,
    user_id: int | None = None,
    chat_id: int | None = None,
) -> dict[str, Any]:
    db = get_db()
    try:
        stmt = select(Embedding).order_by(Embedding.embedding.cosine_distance(Vector(query_embedding))).limit(n_results)
        
        conditions = []
        if user_id is not None:
            conditions.append(Embedding.user_id == user_id)
        if chat_id is not None:
            conditions.append(Embedding.chat_id == chat_id)
        
        if conditions:
            stmt = stmt.where(and_(*conditions))
        
        results = db.execute(stmt).scalars().all()
        
        return {
            "ids": [[str(r.id) for r in results]],
            "documents": [[r.content for r in results]],
            "metadatas": [[
                {
                    "page": r.chunk_metadata.get("page", 0) if r.chunk_metadata else 0,
                    "filename": r.chunk_metadata.get("filename", "unknown") if r.chunk_metadata else "unknown",
                    "document_id": r.document_id,
                    "chat_id": r.chat_id,
                }
                for r in results
            ]],
            "distances": [[float(r.embedding.cosine_distance(Vector(query_embedding))) for r in results]] if results else [[]],
        }
    finally:
        db.close()