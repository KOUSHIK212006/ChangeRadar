"""Unit and integration tests for background research worker, queue, and retry policies."""

import uuid
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import OwnershipScope, ResearchJobStatus, ResearchResultStatus
from app.models.research_job import ResearchJob
from app.models.research_result import ResearchResult
from app.models.research_session import ResearchSession
from app.models.user import User
from app.worker.processor import MockResearchProcessor
from app.worker.queue import JobQueueManager, utc_now
from app.worker.service import ResearchWorker
from tests.test_api_v1 import create_test_user, get_auth_headers


def test_worker_processes_job_successfully(db_session: Session):
    """Verify that worker claims pending job, updates progress, and creates ResearchResult."""
    user = User(email="worker_test@changeradar.ai", full_name="Worker Tester")
    db_session.add(user)
    db_session.commit()

    session = ResearchSession(
        title="Acme Corp Due Diligence",
        target_name="Acme Corp",
        meeting_context="M&A evaluation",
        owner_user_id=user.id,
        scope=OwnershipScope.PERSONAL,
    )
    db_session.add(session)
    db_session.commit()

    job = ResearchJob(
        session_id=session.id,
        status=ResearchJobStatus.PENDING,
        stage="pending",
        attempt_count=0,
        max_attempts=3,
    )
    db_session.add(job)
    db_session.commit()

    job_id = job.id
    session_id = session.id

    # Create worker with in-memory session factory
    worker = ResearchWorker(
        worker_id="test-worker-1",
        processor=MockResearchProcessor(simulate_delay=0.0),
        session_factory=lambda: db_session,
    )

    # Process next job
    processed = worker.process_next_job()
    assert processed is True

    # Re-query job and check states
    updated_job = (
        db_session.query(ResearchJob)
        .filter(ResearchJob.id == job_id)
        .first()
    )
    assert updated_job is not None
    assert updated_job.status == ResearchJobStatus.COMPLETED
    assert updated_job.stage == "completed"
    assert updated_job.progress_percent == 100
    assert updated_job.attempt_count == 1
    assert updated_job.claimed_by == "test-worker-1"
    assert updated_job.completed_at is not None

    # Verify ResearchResult was persisted and linked
    result = (
        db_session.query(ResearchResult)
        .filter(ResearchResult.session_id == session_id)
        .first()
    )
    assert result is not None
    assert result.job_id == job_id
    assert result.research_status == ResearchResultStatus.COMPLETED
    assert "Acme Corp" in result.summary
    assert len(result.key_developments) > 0
    assert len(result.sources) > 0
    assert len(result.claims_and_evidence) > 0


def test_safe_job_claiming_avoids_duplicate_processing(db_session: Session):
    """Verify that once a worker claims a job, a second worker cannot claim the same job."""
    user = User(email="claim_test@changeradar.ai")
    db_session.add(user)
    db_session.commit()

    session = ResearchSession(
        title="Single Job Concurrency Test",
        target_name="Unique Target",
        owner_user_id=user.id,
    )
    db_session.add(session)
    db_session.commit()

    job = ResearchJob(
        session_id=session.id,
        status=ResearchJobStatus.PENDING,
        stage="pending",
    )
    db_session.add(job)
    db_session.commit()

    # First worker claims
    claimed_job = JobQueueManager.claim_next_job(db_session, worker_id="worker-A")
    assert claimed_job is not None
    assert claimed_job.id == job.id
    assert claimed_job.status == ResearchJobStatus.RUNNING
    assert claimed_job.claimed_by == "worker-A"

    # Second worker attempts to claim
    second_claim = JobQueueManager.claim_next_job(db_session, worker_id="worker-B")
    assert second_claim is None


def test_worker_retry_handling_transient_failure(db_session: Session):
    """Verify exponential backoff retry scheduling and permanent failure after max attempts."""
    user = User(email="retry_test@changeradar.ai")
    db_session.add(user)
    db_session.commit()

    session = ResearchSession(
        title="Flaky Service Test",
        target_name="Flaky API",
        owner_user_id=user.id,
    )
    db_session.add(session)
    db_session.commit()

    job = ResearchJob(
        session_id=session.id,
        status=ResearchJobStatus.PENDING,
        stage="pending",
        attempt_count=0,
        max_attempts=3,
    )
    db_session.add(job)
    db_session.commit()

    # Mock processor that always fails
    class FailingProcessor:
        def process(self, job, session, on_progress=None):
            raise ConnectionError("Search provider API timeout (504)")

    worker = ResearchWorker(
        worker_id="retry-worker",
        processor=FailingProcessor(),
        session_factory=lambda: db_session,
        base_retry_delay_seconds=2,
    )

    # Attempt 1: Fails -> Schedules retry (attempt 1/3)
    worker.process_next_job()
    job_1 = db_session.query(ResearchJob).filter(ResearchJob.id == job.id).first()
    assert job_1.status == ResearchJobStatus.RETRY_WAIT
    assert job_1.stage == "retry_wait"
    assert job_1.attempt_count == 1
    assert "Search provider API timeout" in job_1.error_message
    assert job_1.next_retry_at is not None

    # Simulate waiting past next_retry_at
    job_1.next_retry_at = utc_now()
    db_session.commit()

    # Attempt 2: Fails -> Schedules retry (attempt 2/3)
    worker.process_next_job()
    job_2 = db_session.query(ResearchJob).filter(ResearchJob.id == job.id).first()
    assert job_2.status == ResearchJobStatus.RETRY_WAIT
    assert job_2.attempt_count == 2

    # Simulate waiting past next_retry_at
    job_2.next_retry_at = utc_now()
    db_session.commit()

    # Attempt 3: Fails -> Reaches max_attempts (3) -> Permanently FAILED
    worker.process_next_job()
    job_3 = db_session.query(ResearchJob).filter(ResearchJob.id == job.id).first()
    assert job_3.status == ResearchJobStatus.FAILED
    assert job_3.stage == "failed"
    assert job_3.attempt_count == 3
    assert job_3.completed_at is not None


def test_end_to_end_api_and_worker_flow(client: TestClient, db_session: Session):
    """Verify complete lifecycle: POST /research -> check job -> worker processes -> fetch result."""
    user = create_test_user(db_session, "e2e@changeradar.ai", "password123")
    headers = get_auth_headers(client, "e2e@changeradar.ai", "password123")

    # 1. User submits research request
    create_resp = client.post(
        "/api/v1/research",
        json={
            "title": "Nvidia Competitor Pulse",
            "target_name": "Nvidia",
            "target_type": "company",
            "meeting_context": "Pre-meeting briefing for semiconductor partner",
            "time_window": "past_30_days",
            "research_questions": ["What are current datacenter GPU delivery lead times?"],
            "talking_points": ["Demand remains strong across hyperscalers."],
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    create_data = create_resp.json()

    session_id = create_data["session_id"]
    job_id = create_data["job_id"]
    assert session_id is not None
    assert job_id is not None

    # 2. Check initial job status via API -> PENDING
    job_resp = client.get(f"/api/v1/jobs/{job_id}", headers=headers)
    assert job_resp.status_code == 200
    assert job_resp.json()["status"] in ["PENDING", "QUEUED"]
    assert job_resp.json()["progress_percent"] == 0

    # 3. Querying result before completion returns 404 with status
    result_early = client.get(f"/api/v1/research/{session_id}/result", headers=headers)
    assert result_early.status_code == 404
    assert result_early.json()["error"]["code"] == "RESULT_NOT_READY"

    # 4. Background worker executes and completes the job
    worker = ResearchWorker(
        worker_id="e2e-worker",
        processor=MockResearchProcessor(simulate_delay=0.0),
        session_factory=lambda: db_session,
    )
    did_work = worker.process_next_job()
    assert did_work is True

    # 5. Check job status via API -> COMPLETED
    job_done = client.get(f"/api/v1/jobs/{job_id}", headers=headers)
    assert job_done.status_code == 200
    assert job_done.json()["status"] == "COMPLETED"
    assert job_done.json()["progress_percent"] == 100

    # 6. Retrieve synthesized result via API -> 200 OK
    result_resp = client.get(f"/api/v1/research/{session_id}/result", headers=headers)
    assert result_resp.status_code == 200
    result_data = result_resp.json()
    assert result_data["research_status"] == "COMPLETED"
    assert "Nvidia" in result_data["summary"]
    assert len(result_data["key_developments"]) > 0

    # 7. Retrieve events via API -> 200 OK
    events_resp = client.get(f"/api/v1/research/{session_id}/events", headers=headers)
    assert events_resp.status_code == 200
    assert events_resp.json()["total"] > 0

    # 8. Retrieve claims via API -> 200 OK
    claims_resp = client.get(f"/api/v1/research/{session_id}/claims", headers=headers)
    assert claims_resp.status_code == 200
    assert claims_resp.json()["total"] > 0

    # 9. Retrieve briefing via API -> 200 OK (verifying mock processor produces valid IntelligenceResult)
    briefing_resp = client.get(f"/api/v1/sessions/{session_id}/briefing", headers=headers)
    assert briefing_resp.status_code == 200
    briefing_data = briefing_resp.json()
    assert briefing_data["status"] == "COMPLETED"
    assert len(briefing_data["sources"]) > 0
    assert len(briefing_data["events"]) > 0
    assert len(briefing_data["claims"]) > 0


def test_mock_processor_briefing_schema_compatibility(client: TestClient, db_session: Session):
    """Regression Test (Phase 1): Ensure MockResearchProcessor persists valid IntelligenceResult contract.

    Verifies:
    1. Research session creation (/research) enqueues a job.
    2. MockResearchProcessor claims and completes the job.
    3. Structured results are persisted in ResearchResult and raw_intelligence.
    4. Briefing endpoint (/sessions/{session_id}/briefing) returns HTTP 200 with valid IntelligenceResult.
    5. Events endpoint (/research/{session_id}/events) returns HTTP 200 with events list.
    6. Claims endpoint (/research/{session_id}/claims) returns HTTP 200 with claims list.
    7. Result endpoint (/research/{session_id}/result) returns HTTP 200 with full result.
    """
    user = create_test_user(db_session, "mock_briefing_regression@changeradar.ai", "password123")
    headers = get_auth_headers(client, "mock_briefing_regression@changeradar.ai", "password123")

    # 1. Create personal research session
    create_resp = client.post(
        "/api/v1/research",
        json={
            "target_name": "Anthropic PBC",
            "target_type": "company",
            "meeting_context": "Pre-meeting technical evaluation and safety audit",
            "time_window": "30 days",
            "research_questions": ["What is their safety posture?", "Recent funding rounds?"],
            "talking_points": ["Anthropic operates as a Public Benefit Corporation."],
            "scope": "PERSONAL",
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    sess_data = create_resp.json()
    session_id = sess_data["session_id"]
    job_id = sess_data["job_id"]

    # 2. Worker executes job using MockResearchProcessor
    worker = ResearchWorker(
        worker_id="mock-compat-worker",
        processor=MockResearchProcessor(simulate_delay=0.0),
        session_factory=lambda: db_session,
    )
    processed = worker.process_next_job()
    assert processed is True

    # 3. Job status check -> COMPLETED
    job_resp = client.get(f"/api/v1/jobs/{job_id}", headers=headers)
    assert job_resp.status_code == 200
    assert job_resp.json()["status"] == "COMPLETED"
    assert job_resp.json()["progress_percent"] == 100

    # 4. Result retrieval -> HTTP 200
    result_resp = client.get(f"/api/v1/research/{session_id}/result", headers=headers)
    assert result_resp.status_code == 200
    result_json = result_resp.json()
    assert result_json["research_status"] == "COMPLETED"
    assert "Anthropic PBC" in result_json["summary"]

    # 5. Briefing retrieval -> HTTP 200 (Previously failed with 404 due to schema mismatch)
    briefing_resp = client.get(f"/api/v1/sessions/{session_id}/briefing", headers=headers)
    assert briefing_resp.status_code == 200
    briefing = briefing_resp.json()
    assert briefing["session_id"] == session_id
    assert briefing["job_id"] == job_id
    assert briefing["status"] == "COMPLETED"
    assert len(briefing["sources"]) >= 3
    assert len(briefing["origins"]) >= 3
    assert len(briefing["events"]) >= 2
    assert len(briefing["claims"]) >= 3
    assert briefing["coverage"] is not None
    assert briefing["coverage"]["executed_searches"] >= 4
    assert briefing["briefing_summary"] is not None
    assert "Anthropic PBC" in briefing["briefing_summary"]

    # 6. Events retrieval -> HTTP 200
    events_resp = client.get(f"/api/v1/research/{session_id}/events", headers=headers)
    assert events_resp.status_code == 200
    events_json = events_resp.json()
    assert events_json["total"] >= 2
    assert len(events_json["events"]) >= 2
    assert any("Anthropic PBC" in e.get("title", "") for e in events_json["events"])

    # 7. Claims retrieval -> HTTP 200
    claims_resp = client.get(f"/api/v1/research/{session_id}/claims", headers=headers)
    assert claims_resp.status_code == 200
    claims_json = claims_resp.json()
    assert claims_json["total"] >= 3
    assert len(claims_json["claims"]) >= 3

    # 8. Filtered claims retrieval -> HTTP 200
    filtered_claims = client.get(
        f"/api/v1/research/{session_id}/claims?verification_status=SUPPORTED",
        headers=headers,
    )
    assert filtered_claims.status_code == 200
    assert filtered_claims.json()["total"] >= 1
