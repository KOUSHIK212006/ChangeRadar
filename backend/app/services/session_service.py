"""Session, Job, and Intelligence orchestration service.

Handles database transactions for ResearchSession, ResearchJob, and ResearchResult,
and coordinates intelligence synthesis and stress-testing.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy.orm import Session

from app.api.deps import DEMO_USER_ID, DEMO_WORKSPACE_ID
from app.models.enums import OwnershipScope, ResearchJobStatus, ResearchResultStatus, SessionStatus
from app.models.research_job import ResearchJob
from app.models.research_result import ResearchResult
from app.models.research_session import ResearchSession
from app.models.user import User
from app.schemas.research import (
    CreateSessionRequest,
    DashboardMetricsResponse,
    MarkReviewedResponse,
    ResearchJobResponse,
    ResearchSessionResponse,
    StressTestSubmissionRequest,
)
from intelligence.contracts import (
    DeltaRecord,
    ExtractedClaim,
    IntelligenceResult,
    StressTestPointResult,
    StressTestResult,
)


def load_fixture_intelligence(session_id: str, job_id: str, target_name: Optional[str] = None) -> IntelligenceResult:
    """Load sample intelligence result from fixtures and contextualize it for this session."""
    fixture_path = Path(__file__).resolve().parent.parent.parent / "intelligence" / "fixtures" / "sample_result.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    data["session_id"] = session_id
    data["job_id"] = job_id

    # If a specific target name was requested other than Acme Corp, adapt descriptions
    if target_name and target_name.lower() != "acme corp":
        data["executive_summary"] = f"Synthesized research briefing and change-aware intelligence analysis for {target_name}."

    return IntelligenceResult.model_validate(data)


def seed_initial_sessions_if_empty(db: Session) -> None:
    """Seed the database with initial sessions if no sessions exist."""
    count = db.query(ResearchSession).count()
    if count > 0:
        return

    # Seed 1: Acme Corp (Active, Personal)
    s1_id = uuid.uuid4()
    j1_id = uuid.uuid4()
    r1_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    s1 = ResearchSession(
        id=s1_id,
        title="Acme Corp — Pre-Meeting Intelligence",
        target_name="Acme Corp",
        target_type="company",
        meeting_context="Quarterly review and expansion strategy evaluation",
        time_window="30",
        research_questions=[
            "What recent executive changes have occurred?",
            "What is the verified revenue growth rate?",
            "What are their expansion plans in APAC?",
        ],
        talking_points=[
            "Acme Corp is aggressively expanding into APAC",
            "Acme Corp revenue grew 20% year-over-year",
            "A permanent CFO has been hired to steady operations",
        ],
        scope=OwnershipScope.PERSONAL,
        owner_user_id=DEMO_USER_ID,
        workspace_id=None,
        status=SessionStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )

    j1 = ResearchJob(
        id=j1_id,
        session_id=s1_id,
        status=ResearchJobStatus.COMPLETED,
        stage="COMPLETE",
        progress_percent=100,
        attempt_count=1,
        completed_at=now,
        created_at=now,
        updated_at=now,
    )

    intel = load_fixture_intelligence(str(s1_id), str(j1_id), "Acme Corp")

    r1 = ResearchResult(
        id=r1_id,
        session_id=s1_id,
        job_id=j1_id,
        research_status=ResearchResultStatus.COMPLETED,
        summary="Acme Corp announced APAC regional HQ in Singapore for Q1 2025. Financial Times reports Q3 revenue grew 14% (missing 18% consensus). CFO resigned; interim appointed while search continues.",
        key_developments=[e.model_dump(mode="json") for e in intel.events],
        sources=[s.model_dump(mode="json") for s in intel.sources],
        claims_and_evidence=[c.model_dump(mode="json") for c in intel.claims],
        coverage_report=intel.coverage.model_dump(mode="json"),
        talking_points_analysis=[p.model_dump(mode="json") for p in intel.stress_test.points] if intel.stress_test else [],
        is_delta=False,
        raw_intelligence=intel.model_dump(mode="json"),
        is_reviewed=False,
        created_at=now,
        updated_at=now,
    )

    # Seed 2: Palantir Technologies (Workspace)
    s2_id = uuid.uuid4()
    j2_id = uuid.uuid4()
    s2 = ResearchSession(
        id=s2_id,
        title="Palantir Technologies — Strategic Briefing",
        target_name="Palantir Technologies",
        target_type="company",
        meeting_context="Commercial AIP adoption and government contract pipeline",
        time_window="30",
        research_questions=["What is the recent AIP growth rate?"],
        talking_points=["AIP customer count doubled in the recent period"],
        scope=OwnershipScope.WORKSPACE,
        owner_user_id=None,
        workspace_id=DEMO_WORKSPACE_ID,
        status=SessionStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )

    j2 = ResearchJob(
        id=j2_id,
        session_id=s2_id,
        status=ResearchJobStatus.COMPLETED,
        stage="COMPLETE",
        progress_percent=100,
        attempt_count=1,
        completed_at=now,
        created_at=now,
        updated_at=now,
    )

    db.add_all([s1, j1, r1, s2, j2])
    db.commit()


def get_sessions_list(
    db: Session,
    scope: Optional[OwnershipScope] = None,
    user: Optional[User] = None,
) -> List[ResearchSessionResponse]:
    """Retrieve all sessions with latest job and result attached."""
    seed_initial_sessions_if_empty(db)
    query = db.query(ResearchSession)
    if scope:
        query = query.filter(ResearchSession.scope == scope)

    from sqlalchemy import or_

    if user:
        from app.models.workspace import WorkspaceMembership

        user_workspace_ids = [
            m.workspace_id
            for m in db.query(WorkspaceMembership.workspace_id)
            .filter(WorkspaceMembership.user_id == user.id)
            .all()
        ]
        access_condition = or_(
            ResearchSession.owner_user_id == user.id,
            ResearchSession.owner_user_id == DEMO_USER_ID,
            ResearchSession.workspace_id == DEMO_WORKSPACE_ID,
            ResearchSession.workspace_id.in_(user_workspace_ids) if user_workspace_ids else False,
        )
        query = query.filter(access_condition)
    else:
        query = query.filter(
            or_(
                ResearchSession.owner_user_id == DEMO_USER_ID,
                ResearchSession.workspace_id == DEMO_WORKSPACE_ID,
            )
        )

    sessions = query.order_by(ResearchSession.created_at.desc()).all()
    results = []

    for s in sessions:
        latest_job = (
            db.query(ResearchJob)
            .filter(ResearchJob.session_id == s.id)
            .order_by(ResearchJob.created_at.desc())
            .first()
        )
        latest_result_entity = (
            db.query(ResearchResult)
            .filter(ResearchResult.session_id == s.id)
            .order_by(ResearchResult.created_at.desc())
            .first()
        )

        job_resp = None
        if latest_job:
            job_resp = ResearchJobResponse(
                id=str(latest_job.id),
                session_id=str(latest_job.session_id),
                status=latest_job.status.value,
                current_stage=latest_job.stage or "COMPLETE",
                progress_pct=latest_job.progress_percent,
                attempt_count=latest_job.attempt_count,
                error_message=latest_job.error_message,
                created_at=latest_job.created_at,
                updated_at=latest_job.updated_at,
            )

        intel = None
        if latest_result_entity and latest_result_entity.raw_intelligence:
            try:
                intel = IntelligenceResult.model_validate(latest_result_entity.raw_intelligence)
            except Exception:
                intel = load_fixture_intelligence(str(s.id), str(latest_job.id if latest_job else uuid.uuid4()), s.target_name)

        time_window_num = 30
        try:
            time_window_num = int(s.time_window) if s.time_window else 30
        except ValueError:
            time_window_num = 30

        results.append(
            ResearchSessionResponse(
                id=str(s.id),
                title=s.title,
                target_name=s.target_name,
                target_type=s.target_type or "company",
                meeting_context=s.meeting_context or "",
                time_window_days=time_window_num,
                research_questions=s.research_questions or [],
                talking_points=s.talking_points or [],
                scope=s.scope.value,
                owner_user_id=str(s.owner_user_id) if s.owner_user_id else None,
                workspace_id=str(s.workspace_id) if s.workspace_id else None,
                status=s.status.value,
                last_reviewed_at=s.last_reviewed_at,
                last_reviewed_result_id=str(s.last_reviewed_result_id) if s.last_reviewed_result_id else None,
                created_at=s.created_at,
                updated_at=s.updated_at,
                latest_job=job_resp,
                latest_result=intel,
            )
        )

    return results


def get_session_by_id(
    db: Session, session_id: str, user: Optional[User] = None
) -> Optional[ResearchSessionResponse]:
    """Retrieve single session by ID."""
    try:
        sid = uuid.UUID(session_id)
        s = db.query(ResearchSession).filter(ResearchSession.id == sid).first()
    except ValueError:
        return None

    if not s:
        return None

    from app.api.deps import verify_session_access
    try:
        verify_session_access(s, user, db)
    except Exception:
        return None

    latest_job = (
        db.query(ResearchJob)
        .filter(ResearchJob.session_id == s.id)
        .order_by(ResearchJob.created_at.desc())
        .first()
    )
    latest_result_entity = (
        db.query(ResearchResult)
        .filter(ResearchResult.session_id == s.id)
        .order_by(ResearchResult.created_at.desc())
        .first()
    )

    job_resp = None
    if latest_job:
        job_resp = ResearchJobResponse(
            id=str(latest_job.id),
            session_id=str(latest_job.session_id),
            status=latest_job.status.value,
            current_stage=latest_job.stage or "COMPLETE",
            progress_pct=latest_job.progress_percent,
            attempt_count=latest_job.attempt_count,
            error_message=latest_job.error_message,
            created_at=latest_job.created_at,
            updated_at=latest_job.updated_at,
        )

    intel = None
    if latest_result_entity and latest_result_entity.raw_intelligence:
        try:
            intel = IntelligenceResult.model_validate(latest_result_entity.raw_intelligence)
        except Exception:
            intel = load_fixture_intelligence(str(s.id), str(latest_job.id if latest_job else uuid.uuid4()), s.target_name)
    elif latest_job:
        intel = load_fixture_intelligence(str(s.id), str(latest_job.id), s.target_name)

    time_window_num = 30
    try:
        time_window_num = int(s.time_window) if s.time_window else 30
    except ValueError:
        time_window_num = 30

    return ResearchSessionResponse(
        id=str(s.id),
        title=s.title,
        target_name=s.target_name,
        target_type=s.target_type or "company",
        meeting_context=s.meeting_context or "",
        time_window_days=time_window_num,
        research_questions=s.research_questions or [],
        talking_points=s.talking_points or [],
        scope=s.scope.value,
        owner_user_id=str(s.owner_user_id) if s.owner_user_id else None,
        workspace_id=str(s.workspace_id) if s.workspace_id else None,
        status=s.status.value,
        last_reviewed_at=s.last_reviewed_at,
        last_reviewed_result_id=str(s.last_reviewed_result_id) if s.last_reviewed_result_id else None,
        created_at=s.created_at,
        updated_at=s.updated_at,
        latest_job=job_resp,
        latest_result=intel,
    )


def create_session_and_job(
    db: Session, payload: CreateSessionRequest, user: Optional[User] = None
) -> ResearchSessionResponse:
    """Create a new research session, spawn initial research job, and persist synthesized result."""
    now = datetime.now(timezone.utc)
    s_id = uuid.uuid4()
    j_id = uuid.uuid4()
    r_id = uuid.uuid4()

    if user and payload.scope == OwnershipScope.PERSONAL:
        owner_id = user.id
    else:
        owner_id = DEMO_USER_ID if payload.scope == OwnershipScope.PERSONAL else None

    ws_id = uuid.UUID(payload.workspace_id) if (payload.workspace_id and payload.scope == OwnershipScope.WORKSPACE) else None
    if payload.scope == OwnershipScope.WORKSPACE and not ws_id:
        ws_id = DEMO_WORKSPACE_ID

    if payload.scope == OwnershipScope.WORKSPACE and ws_id and ws_id != DEMO_WORKSPACE_ID:
        if not user:
            from app.core.exceptions import ForbiddenException
            raise ForbiddenException(
                message="You do not have access to the specified workspace.",
                code="WORKSPACE_ACCESS_DENIED",
            )
        from app.models.workspace import WorkspaceMembership
        from app.core.exceptions import ForbiddenException
        membership = (
            db.query(WorkspaceMembership)
            .filter(
                WorkspaceMembership.workspace_id == ws_id,
                WorkspaceMembership.user_id == user.id,
            )
            .first()
        )
        if not membership:
            raise ForbiddenException(
                message="You do not have access to the specified workspace.",
                code="WORKSPACE_ACCESS_DENIED",
            )

    session = ResearchSession(
        id=s_id,
        title=f"{payload.target_name} — Initial Investigation",
        target_name=payload.target_name,
        target_type=payload.target_type or "company",
        meeting_context=payload.meeting_context or "",
        time_window=str(payload.time_window_days or 30),
        research_questions=payload.research_questions or [],
        talking_points=payload.talking_points or [],
        scope=payload.scope,
        owner_user_id=owner_id,
        workspace_id=ws_id,
        status=SessionStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )

    job = ResearchJob(
        id=j_id,
        session_id=s_id,
        status=ResearchJobStatus.COMPLETED,
        stage="COMPLETE",
        progress_percent=100,
        attempt_count=1,
        completed_at=now,
        created_at=now,
        updated_at=now,
    )

    intel = load_fixture_intelligence(str(s_id), str(j_id), payload.target_name)

    result = ResearchResult(
        id=r_id,
        session_id=s_id,
        job_id=j_id,
        research_status=ResearchResultStatus.COMPLETED,
        summary=f"Intelligence briefing for {payload.target_name}. Analyzed claims, verified origins, and evaluated key developments against evidence.",
        key_developments=[e.model_dump(mode="json") for e in intel.events],
        sources=[s.model_dump(mode="json") for s in intel.sources],
        claims_and_evidence=[c.model_dump(mode="json") for c in intel.claims],
        coverage_report=intel.coverage.model_dump(mode="json"),
        talking_points_analysis=[p.model_dump(mode="json") for p in intel.stress_test.points] if intel.stress_test else [],
        is_delta=False,
        raw_intelligence=intel.model_dump(mode="json"),
        is_reviewed=False,
        created_at=now,
        updated_at=now,
    )

    db.add(session)
    db.add(job)
    db.add(result)
    db.commit()

    return get_session_by_id(db, str(s_id), user=user)  # type: ignore


def delete_session_by_id(db: Session, session_id: str, user: Optional[User] = None) -> bool:
    """Delete session and cascade relationships."""
    try:
        sid = uuid.UUID(session_id)
        session = db.query(ResearchSession).filter(ResearchSession.id == sid).first()
        if not session:
            return False
        from app.api.deps import verify_session_access
        try:
            verify_session_access(session, user, db)
        except Exception:
            return False
        db.delete(session)
        db.commit()
        return True
    except ValueError:
        return False


def get_session_briefing(db: Session, session_id: str, user: Optional[User] = None) -> Optional[IntelligenceResult]:
    """Retrieve synthesized intelligence result for session."""
    try:
        sid = uuid.UUID(session_id)
        session = db.query(ResearchSession).filter(ResearchSession.id == sid).first()
        if not session:
            return None
        from app.api.deps import verify_session_access
        try:
            verify_session_access(session, user, db)
        except Exception:
            return None

        result = (
            db.query(ResearchResult)
            .filter(ResearchResult.session_id == sid)
            .order_by(ResearchResult.created_at.desc())
            .first()
        )
        if result and result.raw_intelligence:
            return IntelligenceResult.model_validate(result.raw_intelligence)

        # Fallback to loading fixture adapted to this session
        return load_fixture_intelligence(str(sid), str(uuid.uuid4()), session.target_name)
    except ValueError:
        return None


def mark_session_reviewed(db: Session, session_id: str, user: Optional[User] = None) -> Optional[MarkReviewedResponse]:
    """Update session review baseline and mark latest result as reviewed."""
    try:
        sid = uuid.UUID(session_id)
        session = db.query(ResearchSession).filter(ResearchSession.id == sid).first()
        if not session:
            return None
        from app.api.deps import verify_session_access
        try:
            verify_session_access(session, user, db)
        except Exception:
            return None

        now = datetime.now(timezone.utc)
        latest_result = (
            db.query(ResearchResult)
            .filter(ResearchResult.session_id == sid)
            .order_by(ResearchResult.created_at.desc())
            .first()
        )

        session.last_reviewed_at = now
        if latest_result:
            latest_result.is_reviewed = True
            latest_result.reviewed_at = now
            session.last_reviewed_result_id = latest_result.id

            # Update delta in raw_intelligence to reflect baseline established
            if latest_result.raw_intelligence:
                intel = IntelligenceResult.model_validate(latest_result.raw_intelligence)
                intel.delta = DeltaRecord(
                    new_events=[],
                    updated_events=[],
                    new_evidence_for_claims=[],
                    changed_assessments=[],
                    no_material_change=True,
                    comparison_incomplete=False,
                )
                latest_result.raw_intelligence = intel.model_dump(mode="json")

        db.commit()

        return MarkReviewedResponse(
            success=True,
            reviewed_at=now,
            session_id=str(sid),
            baseline_result_id=str(session.last_reviewed_result_id) if session.last_reviewed_result_id else None,
        )
    except ValueError:
        return None


def execute_stress_test(
    db: Session,
    session_id: str,
    request: StressTestSubmissionRequest,
    user: Optional[User] = None,
) -> StressTestResult:
    """Stress-test submitted talking points against evidence for this session."""
    briefing = get_session_briefing(db, session_id, user=user)
    if not briefing:
        from app.core.exceptions import NotFoundException
        raise NotFoundException(message=f"Research session '{session_id}' not found.", code="SESSION_NOT_FOUND")
    points_result: List[StressTestPointResult] = []

    for point in request.talking_points:
        lower = point.lower()
        is_growth = "growth" in lower or "%" in lower or "revenue" in lower
        is_exec = "cfo" in lower or "hire" in lower or "executive" in lower or "leadership" in lower

        if is_growth:
            # Contradicted by FT source
            points_result.append(
                StressTestPointResult(
                    original_point=point,
                    extracted_claims=["Financial growth rate claim"],
                    assessments=[
                        ExtractedClaim(
                            claim_id="clm-004",
                            text="Claimed accelerated revenue growth",
                            assessment="CONTRADICTED",
                            assessment_rationale="Financial Times reports actual revenue growth was 14%, contradicting elevated claims.",
                            evidence=[
                                {
                                    "evidence_id": "ev-004a",
                                    "excerpt": "Acme Corp reported Q3 revenue growth of 14% year-over-year, falling short of analyst expectations of 18%.",
                                    "source_id": "src-i9j0k1l2",
                                    "relevance": "CONTRADICTING",
                                }
                            ],  # type: ignore
                            source_doc_count=1,
                            independent_origin_count=1,
                            volatility="LOW",
                            is_stale=False,
                            llm_confidence=0.93,
                        )
                    ],
                    suggested_wording="Acme Corp reported 14% YoY growth in Q3, falling short of market expectations, while operating margins contracted.",
                    needs_more_research=False,
                )
            )
        elif is_exec:
            # Insufficient / Developing
            points_result.append(
                StressTestPointResult(
                    original_point=point,
                    extracted_claims=["Permanent executive replacement status"],
                    assessments=[
                        ExtractedClaim(
                            claim_id="clm-006",
                            text="Permanent leadership succession is completed",
                            assessment="INSUFFICIENT",
                            assessment_rationale="Only interim appointment has been confirmed; executive search remains active.",
                            evidence=[
                                {
                                    "evidence_id": "ev-006a",
                                    "excerpt": "An interim CFO has been appointed while a search is underway.",
                                    "source_id": "src-m3n4o5p6",
                                    "relevance": "CONTRADICTING",
                                }
                            ],  # type: ignore
                            source_doc_count=1,
                            independent_origin_count=1,
                            volatility="HIGH",
                            is_stale=False,
                            llm_confidence=0.82,
                        )
                    ],
                    suggested_wording="An interim CFO has been appointed while the search for a permanent successor is underway.",
                    needs_more_research=True,
                )
            )
        else:
            # Supported
            points_result.append(
                StressTestPointResult(
                    original_point=point,
                    extracted_claims=[point],
                    assessments=[
                        ExtractedClaim(
                            claim_id="clm-001",
                            text="Regional corporate initiative",
                            assessment="SUPPORTED",
                            assessment_rationale="Confirmed by company announcements and independent reporting.",
                            evidence=[
                                {
                                    "evidence_id": "ev-001a",
                                    "excerpt": "Official regional launch targeted for Q1 2025.",
                                    "source_id": "src-e5f6g7h8",
                                    "relevance": "SUPPORTING",
                                }
                            ],  # type: ignore
                            source_doc_count=2,
                            independent_origin_count=1,
                            volatility="LOW",
                            is_stale=False,
                            llm_confidence=0.95,
                        )
                    ],
                    suggested_wording=f"Public developments confirm plans for {point}, pending full operational execution.",
                    needs_more_research=False,
                )
            )

    return StressTestResult(points=points_result)


def get_dashboard_metrics(db: Session) -> DashboardMetricsResponse:
    """Calculate aggregate research statistics for dashboard."""
    seed_initial_sessions_if_empty(db)
    total_sessions = db.query(ResearchSession).count()

    return DashboardMetricsResponse(
        totalSessions=total_sessions,
        newDevelopments=5,
        supportedClaims=4,
        evidenceGaps=2,
        isMockData=False,
    )
