"""Unit and integration tests for SQLAlchemy database models, relationships, and constraints."""

import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    EvidenceVerificationStatus,
    OwnershipScope,
    ResearchJob,
    ResearchJobStatus,
    ResearchResult,
    ResearchResultStatus,
    ResearchSession,
    SessionStatus,
    User,
    Workspace,
    WorkspaceMembership,
    WorkspaceRole,
)


def test_create_user(db_session: Session):
    """Verify User entity creation, timestamps, and default values."""
    user = User(
        email="analyst@changeradar.ai",
        full_name="Research Analyst",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert isinstance(user.id, uuid.UUID)
    assert user.email == "analyst@changeradar.ai"
    assert user.created_at is not None
    assert user.updated_at is not None
    assert user.is_active is True
    assert user.is_verified is False


def test_personal_research_session_creation(db_session: Session):
    """Verify Personal research session belongs exclusively to owner."""
    user = User(email="owner@changeradar.ai", full_name="Solo Researcher")
    db_session.add(user)
    db_session.commit()

    session = ResearchSession(
        title="Q4 Competitor Analysis",
        target_name="Acme Corp",
        target_type="company",
        meeting_context="Upcoming partnership pitch",
        time_window="past_30_days",
        scope=OwnershipScope.PERSONAL,
        owner_user_id=user.id,
        workspace_id=None,
        research_questions=["What is Acme's Q4 revenue?", "Did leadership change?"],
        talking_points=["Acme is expanding into APAC."],
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    assert session.id is not None
    assert session.scope == OwnershipScope.PERSONAL
    assert session.owner_user_id == user.id
    assert session.workspace_id is None
    assert session.owner.email == "owner@changeradar.ai"
    assert session.last_reviewed_at is None


def test_workspace_research_session_creation(db_session: Session):
    """Verify Workspace research session belongs to workspace without owner_user_id."""
    creator = User(email="teamlead@changeradar.ai", full_name="Team Lead")
    db_session.add(creator)
    db_session.commit()

    workspace = Workspace(
        name="Strategy Team",
        slug="strategy-team",
        created_by_user_id=creator.id,
    )
    db_session.add(workspace)
    db_session.commit()

    membership = WorkspaceMembership(
        workspace_id=workspace.id,
        user_id=creator.id,
        role=WorkspaceRole.OWNER,
    )
    db_session.add(membership)
    db_session.commit()

    session = ResearchSession(
        title="Group Market Radar",
        target_name="Enterprise Cloud Market",
        target_type="market",
        scope=OwnershipScope.WORKSPACE,
        owner_user_id=None,
        workspace_id=workspace.id,
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    assert session.scope == OwnershipScope.WORKSPACE
    assert session.workspace_id == workspace.id
    assert session.owner_user_id is None
    assert session.workspace.name == "Strategy Team"


def test_ownership_scope_check_constraint(db_session: Session):
    """Verify that a session cannot violate mutual exclusivity between owner and workspace."""
    user = User(email="check@changeradar.ai")
    db_session.add(user)
    workspace = Workspace(name="Check WS", slug="check-ws")
    db_session.add(workspace)
    db_session.flush()

    user_id = user.id
    workspace_id = workspace.id

    # Case 1: Neither owner_user_id nor workspace_id is provided
    invalid_session_1 = ResearchSession(
        title="Invalid Scope 1",
        target_name="Target 1",
        scope=OwnershipScope.PERSONAL,
        owner_user_id=None,
        workspace_id=None,
    )
    db_session.add(invalid_session_1)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()

    # Re-insert prerequisite records for second check
    user2 = User(email="check2@changeradar.ai")
    workspace2 = Workspace(name="Check WS 2", slug="check-ws-2")
    db_session.add_all([user2, workspace2])
    db_session.flush()

    # Case 2: Both owner_user_id and workspace_id are provided
    invalid_session_2 = ResearchSession(
        title="Invalid Scope 2",
        target_name="Target 2",
        scope=OwnershipScope.WORKSPACE,
        owner_user_id=user2.id,
        workspace_id=workspace2.id,
    )
    db_session.add(invalid_session_2)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_research_job_lifecycle(db_session: Session):
    """Verify ResearchJob execution state, attempt increments, and heartbeat tracking."""
    user = User(email="jobtest@changeradar.ai")
    db_session.add(user)
    db_session.commit()

    session = ResearchSession(
        title="Job Tracking Test",
        target_name="Beta Technologies",
        owner_user_id=user.id,
    )
    db_session.add(session)
    db_session.commit()

    job = ResearchJob(
        session_id=session.id,
        status=ResearchJobStatus.QUEUED,
        stage="queued",
        attempt_count=0,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    assert job.status == ResearchJobStatus.QUEUED
    assert job.attempt_count == 0

    # Simulate worker claim
    now = datetime.now(timezone.utc)
    job.status = ResearchJobStatus.RUNNING
    job.stage = "searching"
    job.claimed_at = now
    job.claimed_by = "worker-pid-1234"
    job.heartbeat_at = now
    job.attempt_count = 1
    job.progress_percent = 30
    db_session.commit()
    db_session.refresh(job)

    assert job.status == ResearchJobStatus.RUNNING
    assert job.stage == "searching"
    assert job.claimed_by == "worker-pid-1234"
    assert job.attempt_count == 1
    assert job.progress_percent == 30


def test_research_result_persistence_and_delta(db_session: Session):
    """Verify research results persist complex findings and support Delta Briefing."""
    user = User(email="deltatester@changeradar.ai")
    db_session.add(user)
    db_session.commit()

    session = ResearchSession(
        title="Delta Test Session",
        target_name="Delta Dynamics",
        owner_user_id=user.id,
    )
    db_session.add(session)
    db_session.commit()

    job1 = ResearchJob(session_id=session.id, status=ResearchJobStatus.COMPLETED)
    db_session.add(job1)
    db_session.commit()

    # 1. Baseline Research Result
    baseline_result = ResearchResult(
        session_id=session.id,
        job_id=job1.id,
        research_status=ResearchResultStatus.COMPLETED,
        summary="Initial briefing on Delta Dynamics.",
        key_developments=[
            {"id": "ev-1", "title": "Series B Funding Announced", "event_date": "2026-10-15"}
        ],
        sources=[
            {"url": "https://news.example.com/delta-b", "publisher": "TechRadar", "independent_origin_id": "origin-1"}
        ],
        claims_and_evidence=[
            {
                "claim": "Delta Dynamics raised $50M in Series B",
                "verification_status": EvidenceVerificationStatus.SUPPORTED.value,
                "evidence": "Press release confirmed lead investor",
            }
        ],
        coverage_report={"searches_executed": 3, "known_gaps": []},
        is_delta=False,
    )
    db_session.add(baseline_result)
    db_session.commit()
    db_session.refresh(baseline_result)

    assert baseline_result.id is not None
    assert baseline_result.research_status == ResearchResultStatus.COMPLETED
    assert baseline_result.is_delta is False

    # Mark baseline as reviewed
    review_time = datetime.now(timezone.utc)
    baseline_result.is_reviewed = True
    baseline_result.reviewed_at = review_time
    baseline_result.reviewed_by_user_id = user.id

    session.last_reviewed_at = review_time
    session.last_reviewed_result_id = baseline_result.id
    db_session.commit()

    # 2. Subsequent Run - Delta Result comparing against baseline
    job2 = ResearchJob(session_id=session.id, status=ResearchJobStatus.COMPLETED)
    db_session.add(job2)
    db_session.commit()

    delta_result = ResearchResult(
        session_id=session.id,
        job_id=job2.id,
        baseline_result_id=baseline_result.id,
        research_status=ResearchResultStatus.COMPLETED,
        summary="Update: Delta Dynamics acquired AI competitor.",
        is_delta=True,
        delta_summary={
            "new_developments_count": 1,
            "updated_claims_count": 0,
            "new_developments": [
                {"id": "ev-2", "title": "Acquisition of SmartAI", "event_date": "2026-11-10"}
            ],
        },
        claims_and_evidence=[
            {
                "claim": "Acquisition completed for $15M",
                "verification_status": EvidenceVerificationStatus.PARTIALLY_SUPPORTED.value,
                "evidence": "Secondary report mentions unconfirmed price",
            }
        ],
    )
    db_session.add(delta_result)
    db_session.commit()
    db_session.refresh(delta_result)

    assert delta_result.is_delta is True
    assert delta_result.baseline_result_id == baseline_result.id
    assert delta_result.baseline_result.summary == "Initial briefing on Delta Dynamics."
    assert delta_result.delta_summary["new_developments_count"] == 1
    assert session.last_reviewed_result_id == baseline_result.id
