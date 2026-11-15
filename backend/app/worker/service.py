"""Standalone background worker service independent from FastAPI request lifecycle."""

import logging
import os
import time
import uuid
from typing import Callable, Optional

from sqlalchemy.orm import Session, sessionmaker

from app.core.database import SessionLocal
from app.models.research_session import ResearchSession
from app.worker.processor import MockResearchProcessor, ResearchProcessor
from app.worker.queue import JobQueueManager

logger = logging.getLogger("changeradar.worker.service")


class ResearchWorker:
    """Worker daemon that safely claims, processes, and retires research jobs."""

    def __init__(
        self,
        worker_id: Optional[str] = None,
        processor: Optional[ResearchProcessor] = None,
        session_factory: Callable[[], Session] = SessionLocal,
        poll_interval: float = 1.0,
        base_retry_delay_seconds: int = 5,
    ):
        self.worker_id = worker_id or f"worker-{os.getpid()}-{uuid.uuid4().hex[:6]}"
        self.processor = processor or MockResearchProcessor()
        self.session_factory = session_factory
        self.poll_interval = poll_interval
        self.base_retry_delay_seconds = base_retry_delay_seconds
        self._is_running = False

    def process_next_job(self) -> bool:
        """Attempt to claim and process one pending job. Returns True if a job was processed."""
        db: Session = self.session_factory()
        try:
            job = JobQueueManager.claim_next_job(db, worker_id=self.worker_id)
            if not job:
                return False

            job_id = job.id
            session_id = job.session_id

            session = db.query(ResearchSession).filter(ResearchSession.id == session_id).first()
            if not session:
                JobQueueManager.fail_job(
                    db,
                    job_id,
                    Exception("Associated research session was deleted or not found."),
                )
                return True

            def on_progress(stage: str, percent: int) -> None:
                JobQueueManager.update_progress(db, job_id, stage, percent)

            # Execute intelligence processing pipeline
            try:
                result = self.processor.process(job, session, on_progress=on_progress)
                JobQueueManager.complete_job(db, job_id, result)
            except Exception as proc_exc:
                logger.exception(f"Error during intelligence processing for job '{job_id}': {proc_exc}")
                JobQueueManager.fail_job(
                    db,
                    job_id,
                    proc_exc,
                    base_retry_delay_seconds=self.base_retry_delay_seconds,
                )

            return True
        finally:
            db.close()

    def run_loop(self, max_iterations: Optional[int] = None) -> None:
        """Continuous execution loop that polls for work until stopped."""
        self._is_running = True
        logger.info(f"ResearchWorker '{self.worker_id}' started polling queue (interval: {self.poll_interval}s)...")

        iterations = 0
        try:
            while self._is_running:
                did_work = self.process_next_job()
                iterations += 1

                if max_iterations is not None and iterations >= max_iterations:
                    break

                if not did_work:
                    time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            logger.info("Worker received shutdown signal.")
        finally:
            self._is_running = False
            logger.info(f"ResearchWorker '{self.worker_id}' stopped.")

    def stop(self) -> None:
        """Signal the worker loop to cleanly exit."""
        self._is_running = False
