"""Recover background tasks orphaned by a process restart.

Ingestion and summary jobs run in-process (BackgroundTasks / threads). When the
server restarts (deploys, free-tier spin-down) running jobs die silently and
their rows stay "pending"/"processing" forever, so the frontend polls until it
times out. On startup, mark such rows as failed so users get a clear message.
"""
import logging

from sqlalchemy import func, text, update
from sqlalchemy.orm import Session

from app.models.ingestion_task import IngestionTask
from app.models.summary_task import SummaryTask

logger = logging.getLogger(__name__)

INTERRUPTED_MESSAGE = "Processing was interrupted by a server restart. Please try again."
# Rows touched more recently may belong to an instance that is still running
# (e.g. during a zero-downtime deploy).
GRACE_INTERVAL = text("interval '2 minutes'")


def fail_interrupted_tasks(db: Session) -> tuple[int, int]:
    cutoff = func.now() - GRACE_INTERVAL
    ingestion = db.execute(
        update(IngestionTask)
        .where(
            IngestionTask.status.in_(("pending", "processing")),
            func.coalesce(IngestionTask.updated_at, IngestionTask.created_at) < cutoff,
        )
        .values(status="failed", error_message=INTERRUPTED_MESSAGE)
        .execution_options(synchronize_session=False)
    ).rowcount
    summaries = db.execute(
        update(SummaryTask)
        .where(SummaryTask.status.in_(("pending", "processing")), SummaryTask.created_at < cutoff)
        .values(status="error", error=INTERRUPTED_MESSAGE, completed_at=func.now())
        .execution_options(synchronize_session=False)
    ).rowcount
    db.commit()
    if ingestion or summaries:
        logger.warning(
            "Marked %d ingestion and %d summary tasks as interrupted", ingestion, summaries
        )
    return ingestion, summaries
