from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, JSON, Index, text
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
    # Job queue bookkeeping (see app/core/job_queue.py)
    params = Column(JSON, nullable=True)  # n_results / max_tokens for the worker
    attempts = Column(Integer, nullable=False, server_default=text("0"), default=0)
    locked_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("ix_summary_tasks_status", "status"),)
