from sqlalchemy import Boolean, Column, Integer, String, Text, ForeignKey, DateTime, Index, text
from sqlalchemy.sql import func
from app.database import Base


class IngestionTask(Base):
    __tablename__ = "ingestion_tasks"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    filename = Column(String, nullable=False)
    status = Column(String, default="pending")
    chunks_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    file_path = Column(String, nullable=True)
    storage_path = Column(String, nullable=True)
    # Job queue bookkeeping (see app/core/job_queue.py)
    use_ocr = Column(Boolean, nullable=False, server_default=text("false"), default=False)
    attempts = Column(Integer, nullable=False, server_default=text("0"), default=0)
    locked_at = Column(DateTime(timezone=True), nullable=True)  # heartbeat of the worker running it
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL", name="fk_ingestion_tasks_document_id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (Index("ix_ingestion_tasks_status", "status"),)
