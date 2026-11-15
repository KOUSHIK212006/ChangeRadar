"""PostgreSQL-backed safe job queue management with concurrency locking and retry policies."""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.enums import ResearchJobStatus
from app.models.research_job import ResearchJob
from app.models.research_result import ResearchResult

logger = logging.getLogger("changeradar.worker.queue")


def utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


class JobQueueManager:
    """Manages transactional job claiming, progress updates, completion, and retries."""

    @staticmethod
    def claim_next_job(db: Session, worker_id: str) -> Optional[ResearchJob]:
        """Claim the next available pending or retryable job using safe row-level locking."""
        now = utc_now()

        # Eligible statuses for claiming
        claimable_statuses = [
            ResearchJobStatus.PENDING,
            ResearchJobStatus.QUEUED,
            ResearchJobStatus.RETRY_WAIT,
        ]

        query = (
            db.query(ResearchJob)
            .filter(
                ResearchJob.status.in_(claimable_statuses),
                or_(
                    ResearchJob.next_retry_at.is_(None),
                    ResearchJob.next_retry_at <= now,
                ),
            )
            .order_by(ResearchJob.created_at.asc())
        )

        # In PostgreSQL, use SKIP LOCKED to safely support multiple concurrent workers without blocking
        if db.bind and db.bind.dialect.name == "postgresql":
            query = query.with_for_update(skip_locked=True)

        job = query.first()
        if not job:
            return None

        # Transition job to RUNNING
        job.status = ResearchJobStatus.RUNNING
        job.stage = "claimed"
        job.claimed_at = now
        job.claimed_by = worker_id
        job.heartbeat_at = now
        job.attempt_count += 1
        job.error_message = None

        db.commit()
        db.refresh(job)

        logger.info(
            f"Worker '{worker_id}' successfully claimed job '{job.id}' (attempt {job.attempt_count}/{job.max_attempts})"
        )
        return job

    @staticmethod
    def update_progress(
        db: Session,
        job_id: uuid.UUID,
        stage: str,
        progress_percent: int,
    ) -> None:
        """Update job stage, progress percentage, and lease heartbeat."""
        job = db.query(ResearchJob).filter(ResearchJob.id == job_id).first()
        if not job:
            return

        job.stage = stage
        job.progress_percent = min(100, max(0, progress_percent))
        job.heartbeat_at = utc_now()

        db.commit()
        logger.debug(f"Job '{job_id}' progress: [{progress_percent}%] {stage}")

    @staticmethod
    def complete_job(
        db: Session,
        job_id: uuid.UUID,
        result: ResearchResult,
    ) -> None:
        """Persist the research result and mark the job as COMPLETED."""
        job = db.query(ResearchJob).filter(ResearchJob.id == job_id).first()
        if not job:
            return

        now = utc_now()

        # Persist result associated with session and job
        result.job_id = job.id
        result.session_id = job.session_id
        db.add(result)
        db.flush()

        job.status = ResearchJobStatus.COMPLETED
        job.stage = "completed"
        job.progress_percent = 100
        job.completed_at = now
        job.heartbeat_at = now

        db.commit()
        logger.info(f"Job '{job_id}' successfully completed and result '{result.id}' persisted.")

    @staticmethod
    def fail_job(
        db: Session,
        job_id: uuid.UUID,
        error: Exception,
        base_retry_delay_seconds: int = 5,
    ) -> bool:
        """Record an error and schedule a retry or permanently mark as FAILED.

        Returns True if a retry was scheduled, or False if maximum attempts were reached.
        """
        job = db.query(ResearchJob).filter(ResearchJob.id == job_id).first()
        if not job:
            return False

        now = utc_now()
        error_str = str(error)

        if job.attempt_count < job.max_attempts:
            # Exponential backoff: base * 2^(attempt - 1)
            backoff_seconds = base_retry_delay_seconds * (2 ** (job.attempt_count - 1))
            job.status = ResearchJobStatus.RETRY_WAIT
            job.stage = "retry_wait"
            job.next_retry_at = now + timedelta(seconds=backoff_seconds)
            job.error_message = error_str
            job.heartbeat_at = now

            db.commit()
            logger.warning(
                f"Job '{job_id}' failed on attempt {job.attempt_count}/{job.max_attempts}. "
                f"Scheduled retry in {backoff_seconds}s at {job.next_retry_at}. Error: {error_str}"
            )
            return True
        else:
            job.status = ResearchJobStatus.FAILED
            job.stage = "failed"
            job.completed_at = now
            job.error_message = error_str
            job.heartbeat_at = now

            db.commit()
            logger.error(
                f"Job '{job_id}' permanently FAILED after {job.attempt_count} attempts. Error: {error_str}"
            )
            return False
