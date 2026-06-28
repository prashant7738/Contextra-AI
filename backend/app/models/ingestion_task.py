from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
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
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
