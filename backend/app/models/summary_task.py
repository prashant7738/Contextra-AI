from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, JSON
from sqlalchemy.sql import func
from app.database import Base


class SummaryTask(Base):
    __tablename__ = "summary_tasks"

    id = Column(String, primary_key=True)  # UUID string
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    topic_name = Column(String, nullable=False, default="all")
    status = Column(String, nullable=False, default="pending")  # pending | processing | done | error
    result = Column(JSON, nullable=True)  # Stores DetailedSummaryResponse JSON dict
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
