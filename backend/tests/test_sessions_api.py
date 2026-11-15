"""Integration and endpoint verification tests for Sessions, Briefings, and Stress-Testing."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.enums import OwnershipScope
from app.schemas.research import CreateSessionRequest, StressTestSubmissionRequest
from app.services import session_service


@pytest.fixture
def db_session():
    """Create fresh isolated SQLite database per test."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)


def test_list_sessions_seeds_default_data(db_session):
    """Test that listing sessions auto-seeds realistic baseline sessions if empty."""
    sessions = session_service.get_sessions_list(db_session)
    assert len(sessions) >= 2

    # Check Personal Acme session
    acme = next((s for s in sessions if s.target_name == "Acme Corp"), None)
    assert acme is not None
    assert acme.scope == "PERSONAL"
    assert acme.target_type == "company"
    assert len(acme.research_questions) == 3
    assert len(acme.talking_points) == 3
    assert acme.latest_job is not None
    assert acme.latest_job.status == "COMPLETED"
    assert acme.latest_result is not None


def test_list_sessions_with_scope_filter(db_session):
    """Test filtering sessions by PERSONAL and WORKSPACE ownership."""
    personal_sessions = session_service.get_sessions_list(db_session, scope=OwnershipScope.PERSONAL)
    assert all(s.scope == "PERSONAL" for s in personal_sessions)

    workspace_sessions = session_service.get_sessions_list(db_session, scope=OwnershipScope.WORKSPACE)
    assert all(s.scope == "WORKSPACE" for s in workspace_sessions)


def test_create_session_lifecycle(db_session):
    """Test creating a new session and initiating investigation."""
    payload = CreateSessionRequest(
        target_name="Stripe, Inc.",
        target_type="company",
        meeting_context="Enterprise billing API partnership",
        time_window_days=60,
        research_questions=["What are the latest enterprise pricing updates?"],
        talking_points=["Stripe reduced cross-border fees"],
        scope=OwnershipScope.PERSONAL,
    )

    created = session_service.create_session_and_job(db_session, payload)
    assert created.id is not None
    assert created.target_name == "Stripe, Inc."
    assert created.time_window_days == 60
    assert created.scope == "PERSONAL"
    assert created.latest_job is not None
    assert created.latest_job.status == "COMPLETED"
    assert created.latest_result is not None

    # Verify retrieval
    retrieved = session_service.get_session_by_id(db_session, created.id)
    assert retrieved is not None
    assert retrieved.id == created.id


def test_get_session_briefing_contract(db_session):
    """Verify synthesized briefing adheres to IntelligenceResult schema."""
    sessions = session_service.get_sessions_list(db_session)
    acme_session = sessions[0]

    briefing = session_service.get_session_briefing(db_session, acme_session.id)
    assert briefing is not None
    assert briefing.status == "COMPLETED"
    assert len(briefing.sources) >= 4
    assert len(briefing.origins) >= 3
    assert len(briefing.events) >= 3
    assert len(briefing.claims) >= 6

    # Verify coverage report
    assert briefing.coverage.planned_searches >= 5
    assert briefing.coverage.executed_searches >= 5
    assert briefing.coverage.origin_diversity_score > 0

    # Verify independent origin distinction
    apac_press_origin = next(
        (o for o in briefing.origins if "Press Release" in o.label), None
    )
    assert apac_press_origin is not None
    assert apac_press_origin.is_independent is False
    assert len(apac_press_origin.source_ids) >= 2


def test_mark_reviewed_establishes_baseline(db_session):
    """Verify marking briefing as reviewed records timestamp and baseline."""
    sessions = session_service.get_sessions_list(db_session)
    session = sessions[0]

    assert session.last_reviewed_at is None
    review_res = session_service.mark_session_reviewed(db_session, session.id)
    assert review_res is not None
    assert review_res.success is True
    assert review_res.reviewed_at is not None

    # Check updated session state
    updated_session = session_service.get_session_by_id(db_session, session.id)
    assert updated_session.last_reviewed_at is not None
    assert updated_session.last_reviewed_result_id is not None


def test_stress_test_contradiction_detection(db_session):
    """Verify talking points stress testing catches contradicted claims."""
    sessions = session_service.get_sessions_list(db_session)
    session = sessions[0]

    stress_req = StressTestSubmissionRequest(
        talking_points=[
            "Acme Corp revenue grew 20% year-over-year",
            "A permanent CFO replacement has been finalized",
            "Acme Corp is establishing a Singapore presence in 2025",
        ]
    )

    stress_res = session_service.execute_stress_test(db_session, session.id, stress_req)
    assert len(stress_res.points) == 3

    # Point 1: Growth claim should be CONTRADICTED
    pt_growth = stress_res.points[0]
    assert pt_growth.assessments[0].assessment == "CONTRADICTED"
    assert "14%" in pt_growth.suggested_wording

    # Point 2: Executive claim should be INSUFFICIENT with needs_more_research=True
    pt_exec = stress_res.points[1]
    assert pt_exec.assessments[0].assessment == "INSUFFICIENT"
    assert pt_exec.needs_more_research is True

    # Point 3: Singapore presence should be SUPPORTED
    pt_sg = stress_res.points[2]
    assert pt_sg.assessments[0].assessment == "SUPPORTED"
    assert pt_sg.needs_more_research is False


def test_delete_session(db_session):
    """Verify session deletion removes session from database."""
    sessions = session_service.get_sessions_list(db_session)
    session_to_delete = sessions[0]

    success = session_service.delete_session_by_id(db_session, session_to_delete.id)
    assert success is True

    retrieved = session_service.get_session_by_id(db_session, session_to_delete.id)
    assert retrieved is None
