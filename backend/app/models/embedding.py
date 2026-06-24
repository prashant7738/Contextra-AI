from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
from pgvector.sqlalchemy import Vector
from app.database import Base


class Embedding(Base):
    __tablename__ = "embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=True, index=True)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(384), nullable=False)
    chunk_metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_embeddings_user_chat", "user_id", "chat_id"),
        Index("ix_embeddings_embedding_cosine", "embedding", postgresql_using="ivfflat", postgresql_with={"lists": 100}, postgresql_ops={"embedding": "vector_cosine_ops"}),
    )