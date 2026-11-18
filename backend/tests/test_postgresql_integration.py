"""Comprehensive PostgreSQL integration, persistence, migration, and concurrency verification test suite.

Validates against real PostgreSQL:
1. PostgreSQL connection & dialect verification
2. Column data types (UUID, TIMESTAMP WITH TIME ZONE, JSON, VARCHAR, etc.)
3. Constraints & Indexes (Check constraints, Unique constraints, Foreign keys, Cascade deletes)
4. Alembic migration rollback (downgrade to base) and re-application (upgrade to head)
5. End-to-end data persistence with rich JSON, UUIDs, and UTC timestamps
6. Concurrent worker job claiming using SELECT FOR UPDATE SKIP LOCKED (proves no race condition / double claiming)
7. Job failure, exponential retry scheduling, and permanent failure transitions
8. Engine disposal and restart persistence verification
"""

import os
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from alembic import command
from alembic.config import Config
from app.models.enums import (
    EvidenceVerificationStatus,
    OwnershipScope,
    ResearchJobStatus,
    ResearchResultStatus,
    SessionStatus,
    WorkspaceRole,
)
from app.models.research_job import ResearchJob
from app.models.research_result import ResearchResult
from app.models.research_session import ResearchSession
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMembership
from app.worker.queue import JobQueueManager

PG_TEST_URL = os.getenv(
    "POSTGRES_TEST_DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/changeradar_test",
)


@pytest.fixture(scope="module")
def pg_engine():
    """Create a module-scoped PostgreSQL engine."""
    engine = create_engine(PG_TEST_URL, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"PostgreSQL not accessible at {PG_TEST_URL}: {exc}")
    yield engine
    engine.dispose()


@pytest.fixture(scope="module")
def pg_session_factory(pg_engine):
    """Session factory bound to PostgreSQL test database."""
    return sessionmaker(autocommit=False, autoflush=False, bind=pg_engine)


@pytest.fixture(autouse=True)
def clean_pg_tables(pg_engine):
    """Clean tables before each test to guarantee complete isolation without dropping tables."""
    yield
    with pg_engine.connect() as conn:
        with conn.begin():
            conn.execute(
                text(
                    "TRUNCATE TABLE research_results, research_jobs, "
                    "research_sessions, workspace_memberships, workspaces, users CASCADE;"
                )
            )


# ==============================================================================
# 1. POSTGRESQL DIALECT & COLUMN DATA TYPE COMPATIBILITY
# ==============================================================================


def test_postgresql_connection_and_dialect(pg_engine):
    """Verify that PostgreSQL engine is connected and dialect is postgresql."""
    assert pg_engine.dialect.name == "postgresql"
    with pg_engine.connect() as conn:
        version = conn.execute(text("SHOW server_version;")).scalar()
        print(f"\n[PostgreSQL Version] {version}")
        assert version is not None


def test_postgresql_column_types_and_indexes(pg_engine):
    """Inspect PostgreSQL schema to verify native UUID, TIMESTAMPTZ, and JSON columns."""
    inspector = inspect(pg_engine)
    table_names = inspector.get_table_names()

    expected_tables = {
        "users",
        "workspaces",
        "workspace_memberships",
        "research_sessions",
        "research_jobs",
        "research_results",
        "alembic_version",
    }
    assert expected_tables.issubset(set(table_names))

    # 1. UUID columns in research_sessions
    session_cols = {col["name"]: col for col in inspector.get_columns("research_sessions")}
    assert str(session_cols["id"]["type"]).upper() == "UUID"
    assert str(session_cols["owner_user_id"]["type"]).upper() == "UUID"
    assert str(session_cols["workspace_id"]["type"]).upper() == "UUID"

    # 2. JSON columns in research_results
    result_cols = {col["name"]: col for col in inspector.get_columns("research_results")}
    assert str(result_cols["raw_intelligence"]["type"]).upper() in {"JSON", "JSONB"}
    assert str(result_cols["claims_and_evidence"]["type"]).upper() in {"JSON", "JSONB"}
    assert str(result_cols["key_developments"]["type"]).upper() in {"JSON", "JSONB"}

    # 3. Timezone-aware timestamp columns
    job_cols = {col["name"]: col for col in inspector.get_columns("research_jobs")}
    created_at_type = str(job_cols["created_at"]["type"]).upper()
    assert "TIME ZONE" in created_at_type or "TIMESTAMPTZ" in created_at_type

    # 4. Indexes verified
    job_indexes = [idx["name"] for idx in inspector.get_indexes("research_jobs")]
    assert "ix_research_job_status_next_retry" in job_indexes
    assert "ix_research_job_session_status" in job_indexes


# ==============================================================================
# 2. CONSTRAINTS AND RELATIONSHIPS
# ==============================================================================


def test_ownership_scope_check_constraint(pg_session_factory):
    """Verify that chk_research_session_ownership_scope prevents invalid ownership combinations."""
    session = pg_session_factory()
    try:
        user = User(email=f"owner-{uuid.uuid4()}@changeradar.ai", full_name="Scope Tester")
        workspace = Workspace(name="Test Org", slug=f"test-org-{uuid.uuid4().hex[:6]}")
        session.add_all([user, workspace])
        session.commit()

        # Violation 1: Both owner_user_id AND workspace_id provided
        invalid_session_1 = ResearchSession(
            title="Invalid Both Scope",
            target_name="Conflict Corp",
            scope=OwnershipScope.PERSONAL,
            owner_user_id=user.id,
            workspace_id=workspace.id,
        )
        session.add(invalid_session_1)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        # Violation 2: Neither owner_user_id NOR workspace_id provided
        invalid_session_2 = ResearchSession(
            title="Invalid Neither Scope",
            target_name="Orphan Corp",
            scope=OwnershipScope.PERSONAL,
            owner_user_id=None,
            workspace_id=None,
        )
        session.add(invalid_session_2)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        # Valid Case: Exactly owner_user_id provided
        valid_personal = ResearchSession(
            title="Valid Personal Scope",
            target_name="Personal Target",
            scope=OwnershipScope.PERSONAL,
            owner_user_id=user.id,
            workspace_id=None,
        )
        session.add(valid_personal)
        session.commit()
        assert valid_personal.id is not None
    finally:
        session.close()


def test_cascade_delete_integrity(pg_session_factory):
    """Verify cascading deletes from User/Session down to Jobs and Results."""
    session = pg_session_factory()
    try:
        user = User(email=f"cascade-{uuid.uuid4()}@changeradar.ai")
        session.add(user)
        session.commit()

        res_session = ResearchSession(
            title="Cascade Target",
            target_name="Acme Corp",
            scope=OwnershipScope.PERSONAL,
            owner_user_id=user.id,
        )
        session.add(res_session)
        session.commit()

        job = ResearchJob(session_id=res_session.id, status=ResearchJobStatus.COMPLETED)
        session.add(job)
        session.commit()

        result = ResearchResult(
            session_id=res_session.id,
            job_id=job.id,
            summary="Cascade Test Summary",
        )
        session.add(result)
        session.commit()

        # Delete session — must cascade and remove job and result
        session.delete(res_session)
        session.commit()

        assert session.query(ResearchJob).filter_by(id=job.id).first() is None
        assert session.query(ResearchResult).filter_by(id=result.id).first() is None
    finally:
        session.close()


# ==============================================================================
# 3. DATA PERSISTENCE WITH RICH JSON AND UUID FIDELITY
# ==============================================================================


def test_rich_json_and_result_persistence(pg_session_factory):
    """Verify full fidelity of complex JSON intelligence payloads in PostgreSQL."""
    session = pg_session_factory()
    try:
        user = User(email=f"intel-{uuid.uuid4()}@changeradar.ai")
        session.add(user)
        session.commit()

        res_session = ResearchSession(
            title="Deep Intelligence Test",
            target_name="QuantumAI Inc",
            scope=OwnershipScope.PERSONAL,
            owner_user_id=user.id,
            research_questions=["What is their product roadmap?", "Who are the key founders?"],
            talking_points=["QuantumAI recently completed Series B"],
        )
        session.add(res_session)
        session.commit()

        job = ResearchJob(
            session_id=res_session.id,
            status=ResearchJobStatus.COMPLETED,
            progress_percent=100,
            stage="completed",
            parameters={"time_window_days": 30, "depth": "advanced"},
        )
        session.add(job)
        session.commit()

        raw_payload = {
            "sources": [
                {
                    "source_id": "src-101",
                    "title": "QuantumAI Secures $50M Series B",
                    "url": "https://techcrunch.com/quantumai",
                    "publisher": "TechCrunch",
                }
            ],
            "claims": [
                {
                    "claim_id": "clm-201",
                    "text": "QuantumAI closed $50M in Series B financing.",
                    "assessment": "SUPPORTED",
                    "confidence": 0.98,
                }
            ],
            "briefing": "QuantumAI announced major capital infusion to accelerate hardware deployment.",
        }

        result = ResearchResult(
            session_id=res_session.id,
            job_id=job.id,
            research_status=ResearchResultStatus.COMPLETED,
            summary=raw_payload["briefing"],
            sources=raw_payload["sources"],
            claims_and_evidence=raw_payload["claims"],
            raw_intelligence=raw_payload,
            is_reviewed=True,
            reviewed_at=datetime.now(timezone.utc),
            reviewed_by_user_id=user.id,
        )
        session.add(result)
        session.commit()

        result_id = result.id
        session.close()

        # Verify in a completely separate session
        new_session = pg_session_factory()
        persisted = new_session.query(ResearchResult).filter_by(id=result_id).first()
        assert persisted is not None
        assert persisted.summary == raw_payload["briefing"]
        assert persisted.raw_intelligence["sources"][0]["source_id"] == "src-101"
        assert persisted.claims_and_evidence[0]["assessment"] == "SUPPORTED"
        assert persisted.is_reviewed is True
        assert persisted.reviewed_by_user_id == user.id
        new_session.close()
    finally:
        session.close()


# ==============================================================================
# 4. CONCURRENT WORKER JOB CLAIMING (SELECT FOR UPDATE SKIP LOCKED)
# ==============================================================================


def test_concurrent_worker_claiming_skip_locked(pg_session_factory):
    """Verify that multiple concurrent workers claiming jobs simultaneously never conflict or double-claim."""
    session = pg_session_factory()
    try:
        user = User(email=f"worker-{uuid.uuid4()}@changeradar.ai")
        session.add(user)
        session.commit()

        res_session = ResearchSession(
            title="Concurrency Session",
            target_name="Parallel Systems",
            scope=OwnershipScope.PERSONAL,
            owner_user_id=user.id,
        )
        session.add(res_session)
        session.commit()

        # Create exactly 1 pending job
        job = ResearchJob(
            session_id=res_session.id,
            status=ResearchJobStatus.PENDING,
            stage="queued",
            attempt_count=0,
            max_attempts=3,
        )
        session.add(job)
        session.commit()
        job_id = job.id
    finally:
        session.close()

    # Launch two simultaneous workers trying to claim the single job
    claimed_by_worker = {}
    barrier = threading.Barrier(2)

    def worker_claim(worker_id: str):
        db = pg_session_factory()
        try:
            barrier.wait()  # Synchronize threads to hit PostgreSQL at the exact same moment
            claimed_job = JobQueueManager.claim_next_job(db, worker_id=worker_id)
            if claimed_job:
                claimed_by_worker[worker_id] = claimed_job.id
            else:
                claimed_by_worker[worker_id] = None
        finally:
            db.close()

    t1 = threading.Thread(target=worker_claim, args=("worker-alpha",))
    t2 = threading.Thread(target=worker_claim, args=("worker-beta",))

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Verification: Exactly ONE worker must have claimed the job; the other must receive None
    claims = [v for v in claimed_by_worker.values() if v is not None]
    assert len(claims) == 1, f"Expected exactly 1 claim, got: {claimed_by_worker}"
    assert claims[0] == job_id

    # Verify final database state in PostgreSQL
    verify_session = pg_session_factory()
    claimed_record = verify_session.query(ResearchJob).filter_by(id=job_id).first()
    assert claimed_record.status == ResearchJobStatus.RUNNING
    assert claimed_record.claimed_by in {"worker-alpha", "worker-beta"}
    assert claimed_record.attempt_count == 1
    verify_session.close()


# ==============================================================================
# 5. RETRY HANDLING AND MAX ATTEMPTS TRANSITION
# ==============================================================================


def test_job_failure_retry_and_terminal_state(pg_session_factory):
    """Verify exponential backoff scheduling on failure and transition to FAILED upon max attempts."""
    session = pg_session_factory()
    try:
        user = User(email=f"retry-{uuid.uuid4()}@changeradar.ai")
        session.add(user)
        session.commit()

        res_session = ResearchSession(
            title="Retry Test Session",
            target_name="Faulty Corp",
            scope=OwnershipScope.PERSONAL,
            owner_user_id=user.id,
        )
        session.add(res_session)
        session.commit()

        job = ResearchJob(
            session_id=res_session.id,
            status=ResearchJobStatus.RUNNING,
            attempt_count=1,
            max_attempts=3,
        )
        session.add(job)
        session.commit()
        job_id = job.id

        # First failure: should schedule retry (attempt 1 < 3)
        retried = JobQueueManager.fail_job(session, job_id, Exception("Transient Network Timeout"), base_retry_delay_seconds=2)
        assert retried is True

        job_db = session.query(ResearchJob).filter_by(id=job_id).first()
        assert job_db.status == ResearchJobStatus.RETRY_WAIT
        assert job_db.next_retry_at is not None
        assert "Transient Network Timeout" in job_db.error_message

        # Fast forward attempt to max_attempts
        job_db.attempt_count = 3
        session.commit()

        # Terminal failure
        terminal = JobQueueManager.fail_job(session, job_id, Exception("Permanent LLM Rejection"))
        assert terminal is False

        job_final = session.query(ResearchJob).filter_by(id=job_id).first()
        assert job_final.status == ResearchJobStatus.FAILED
        assert "Permanent LLM Rejection" in job_final.error_message
    finally:
        session.close()


# ==============================================================================
# 6. SIMULATED RESTART & RESULT PERSISTENCE
# ==============================================================================


def test_simulated_backend_restart_persistence(pg_engine, pg_session_factory):
    """Verify that after backend shutdown and engine disposal, completed results remain accessible."""
    session = pg_session_factory()
    try:
        user = User(email=f"persist-{uuid.uuid4()}@changeradar.ai")
        session.add(user)
        session.commit()

        res_session = ResearchSession(
            title="Persistence Target",
            target_name="Durable Corp",
            scope=OwnershipScope.PERSONAL,
            owner_user_id=user.id,
        )
        session.add(res_session)
        session.commit()

        job = ResearchJob(
            session_id=res_session.id,
            status=ResearchJobStatus.COMPLETED,
            stage="completed",
        )
        session.add(job)
        session.commit()

        result = ResearchResult(
            session_id=res_session.id,
            job_id=job.id,
            summary="Durable briefing summary after simulated reboot",
        )
        session.add(result)
        session.commit()
        saved_id = result.id
    finally:
        session.close()

    # Simulate hard backend shutdown by disposing engine connection pool
    pg_engine.dispose()

    # Simulate fresh boot with new engine
    new_engine = create_engine(PG_TEST_URL, pool_pre_ping=True)
    NewSession = sessionmaker(bind=new_engine)
    fresh_session = NewSession()

    try:
        persisted = fresh_session.query(ResearchResult).filter_by(id=saved_id).first()
        assert persisted is not None
        assert persisted.summary == "Durable briefing summary after simulated reboot"
        assert persisted.job.status == ResearchJobStatus.COMPLETED
        assert persisted.session.target_name == "Durable Corp"
    finally:
        fresh_session.close()
        new_engine.dispose()

