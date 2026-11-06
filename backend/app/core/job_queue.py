"""Durable job queue backed by the existing task tables in PostgreSQL.

Jobs are the rows of ingestion_tasks (status 'pending') and summary_tasks
(status 'pending'). Worker threads claim one row at a time with
`FOR UPDATE SKIP LOCKED`, so several workers or instances never run the same
job. While a job runs, a heartbeat refreshes its `locked_at`. A reaper puts
jobs whose heartbeat stopped (the process died or was redeployed) back to
'pending' for another attempt, up to MAX_ATTEMPTS, then marks them failed.

No extra infrastructure: it needs only the database the app already uses.
"""
from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass
from typing import Callable

from sqlalchemy import text

from app.database import SessionLocal

logger = logging.getLogger(__name__)

def _env_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, default)))
    except ValueError:
        return default


MAX_ATTEMPTS = _env_int("JOB_MAX_ATTEMPTS", 3)
HEARTBEAT_SECONDS = _env_int("JOB_HEARTBEAT_SECONDS", 20)
# A running job whose heartbeat is older than this is considered abandoned.
STALE_AFTER_SECONDS = _env_int("JOB_STALE_SECONDS", 120)
POLL_SECONDS = _env_int("JOB_POLL_SECONDS", 5)
REAP_EVERY_SECONDS = _env_int("JOB_REAP_SECONDS", 60)

INTERRUPTED_MESSAGE = "Processing was interrupted repeatedly. Please try again."


@dataclass(frozen=True)
class JobKind:
    name: str
    table: str
    running: str
    failed: str
    error_column: str
    claim_order: str
    run: Callable[[object], None]


def _run_ingestion(task_id) -> None:
    from app.services.background_ingestion import process_ingestion_task

    process_ingestion_task(int(task_id))


def _run_summary(task_id) -> None:
    from app.tasks import run_summary_task

    run_summary_task(str(task_id))


KINDS = (
    JobKind("ingestion", "ingestion_tasks", "processing", "failed", "error_message", "id", _run_ingestion),
    JobKind("summary", "summary_tasks", "processing", "error", "error", "created_at", _run_summary),
)

_wakeup = threading.Event()


def notify() -> None:
    """Wake idle workers in this process so a new job starts immediately."""
    _wakeup.set()


def claim_next(db, kind: JobKind):
    """Atomically take the oldest pending job of this kind. Returns its id or None."""
    row = db.execute(
        text(
            f"""
            UPDATE {kind.table}
               SET status = :running, locked_at = now(), attempts = attempts + 1
             WHERE id = (
                   SELECT id FROM {kind.table}
                    WHERE status = 'pending'
                    ORDER BY {kind.claim_order}
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED)
         RETURNING id
            """
        ),
        {"running": kind.running},
    ).first()
    db.commit()
    return row[0] if row else None


def heartbeat(db, kind: JobKind, job_id) -> None:
    db.execute(
        text(f"UPDATE {kind.table} SET locked_at = now() WHERE id = :id AND status = :running"),
        {"id": job_id, "running": kind.running},
    )
    db.commit()


def reap_stale(db, stale_after_seconds: int = STALE_AFTER_SECONDS) -> dict[str, tuple[int, int]]:
    """Requeue (or, after MAX_ATTEMPTS, fail) running jobs whose heartbeat stopped.

    Jobs claimed before the queue existed have no heartbeat at all; they are
    treated the same way.
    """
    summary: dict[str, tuple[int, int]] = {}
    for kind in KINDS:
        stale = (
            f"status = :running AND COALESCE(locked_at, created_at AT TIME ZONE 'UTC') "
            f"< now() - make_interval(secs => :stale)"
        )
        params = {"running": kind.running, "stale": stale_after_seconds, "max": MAX_ATTEMPTS}
        requeued = db.execute(
            text(f"UPDATE {kind.table} SET status = 'pending', locked_at = NULL WHERE {stale} AND attempts < :max"),
            params,
        ).rowcount
        failed = db.execute(
            text(
                f"UPDATE {kind.table} SET status = :failed, locked_at = NULL, {kind.error_column} = :msg "
                f"WHERE {stale} AND attempts >= :max"
            ),
            {**params, "failed": kind.failed, "msg": INTERRUPTED_MESSAGE},
        ).rowcount
        db.commit()
        if requeued or failed:
            logger.warning("Job queue: %s jobs requeued=%d failed=%d after lost heartbeat", kind.name, requeued, failed)
        summary[kind.name] = (requeued, failed)
    return summary


def run_one(db, kind: JobKind) -> bool:
    """Claim and run a single job of this kind. Returns True if one ran."""
    job_id = claim_next(db, kind)
    if job_id is None:
        return False
    stop_beat = threading.Event()

    def beat() -> None:
        with SessionLocal() as beat_db:
            while not stop_beat.wait(HEARTBEAT_SECONDS):
                try:
                    heartbeat(beat_db, kind, job_id)
                except Exception:
                    logger.exception("Heartbeat failed for %s job %s", kind.name, job_id)
                    beat_db.rollback()

    beater = threading.Thread(target=beat, name=f"heartbeat-{kind.name}-{job_id}", daemon=True)
    beater.start()
    try:
        kind.run(job_id)
    except Exception:
        # Handlers record their own failures; this only guards the worker loop.
        logger.exception("%s job %s raised", kind.name, job_id)
    finally:
        stop_beat.set()
        beater.join(timeout=5)
    return True


class Worker:
    """Background worker threads that drain the queue until stopped."""

    def __init__(self, threads: int):
        self.threads = threads
        self._stop = threading.Event()
        self._pool: list[threading.Thread] = []
        self._reaper: threading.Thread | None = None

    def start(self) -> None:
        if self.threads <= 0:
            logger.info("Job queue workers disabled (JOB_WORKERS=0)")
            return
        self._reaper = threading.Thread(target=self._reap_loop, name="job-reaper", daemon=True)
        self._reaper.start()
        for i in range(self.threads):
            thread = threading.Thread(target=self._work_loop, name=f"job-worker-{i}", daemon=True)
            thread.start()
            self._pool.append(thread)
        logger.info("Job queue started with %d worker thread(s)", self.threads)

    def stop(self, timeout: float = 10) -> None:
        self._stop.set()
        _wakeup.set()
        for thread in self._pool + ([self._reaper] if self._reaper else []):
            thread.join(timeout=timeout)

    def _reap_loop(self) -> None:
        while not self._stop.is_set():
            try:
                with SessionLocal() as db:
                    reap_stale(db)
            except Exception:
                logger.exception("Job reaper failed")
            self._stop.wait(REAP_EVERY_SECONDS)

    def _work_loop(self) -> None:
        while not self._stop.is_set():
            ran = False
            try:
                with SessionLocal() as db:
                    for kind in KINDS:
                        if self._stop.is_set():
                            break
                        ran = run_one(db, kind) or ran
            except Exception:
                logger.exception("Job worker loop failed")
            if not ran:
                _wakeup.wait(POLL_SECONDS)
                _wakeup.clear()


def worker_threads_from_env() -> int:
    try:
        return max(0, int(os.getenv("JOB_WORKERS", "2")))
    except ValueError:
        return 2
