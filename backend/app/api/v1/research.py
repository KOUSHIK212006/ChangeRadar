"""Research session, result, event, and claim REST endpoints."""

import math
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, verify_session_access
from app.core.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from app.models.enums import (
    EvidenceVerificationStatus,
    OwnershipScope,
    ResearchJobStatus,
    SessionStatus,
    WorkspaceRole,
)
from app.models.research_job import ResearchJob
from app.models.research_result import ResearchResult
from app.models.research_session import ResearchSession
from app.models.user import User
from app.models.workspace import WorkspaceMembership
from app.schemas.job import ResearchJobResponse
from app.schemas.research import (
    PaginatedResearchSessionsResponse,
    ResearchSessionCreate,
    ResearchSessionCreateResponse,
    ResearchSessionListItemResponse,
    ResearchSessionResponse,
)
from app.schemas.result import ClaimsListResponse, EventsListResponse, ResearchResultResponse

router = APIRouter(prefix="/research", tags=["Research"])


@router.post(
    "",
    response_model=ResearchSessionCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new research session and queue a research job",
)
def create_research_session(
    payload: ResearchSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResearchSessionCreateResponse:
    """Initialize a research session and enqueue a pending background research job."""
    title = payload.title or f"Research: {payload.target_name.strip()}"

    owner_user_id: Optional[uuid.UUID] = None
    workspace_id: Optional[uuid.UUID] = None

    if payload.scope == OwnershipScope.PERSONAL:
        owner_user_id = current_user.id
        workspace_id = None
    elif payload.scope == OwnershipScope.WORKSPACE:
        if not payload.workspace_id:
            raise BadRequestException(
                message="workspace_id is required when scope is WORKSPACE.",
                code="WORKSPACE_ID_REQUIRED",
            )
        # Verify user belongs to requested workspace
        membership = (
            db.query(WorkspaceMembership)
            .filter(
                WorkspaceMembership.workspace_id == payload.workspace_id,
                WorkspaceMembership.user_id == current_user.id,
            )
            .first()
        )
        if not membership:
            raise ForbiddenException(
                message="You do not have access to the specified workspace.",
                code="WORKSPACE_ACCESS_DENIED",
            )
        workspace_id = payload.workspace_id
        owner_user_id = None

    # 1. Create Session
    session = ResearchSession(
        title=title,
        target_name=payload.target_name.strip(),
        target_type=payload.target_type,
        meeting_context=payload.meeting_context,
        time_window=payload.time_window,
        research_questions=payload.research_questions,
        talking_points=payload.talking_points,
        scope=payload.scope,
        owner_user_id=owner_user_id,
        workspace_id=workspace_id,
        status=SessionStatus.ACTIVE,
    )
    db.add(session)
    db.flush()

    # 2. Create Initial Queued Worker Job
    job = ResearchJob(
        session_id=session.id,
        status=ResearchJobStatus.QUEUED,
        stage="queued",
        progress_percent=0,
        attempt_count=0,
        max_attempts=3,
        parameters={
            "target_name": payload.target_name,
            "target_type": payload.target_type,
            "meeting_context": payload.meeting_context,
            "time_window": payload.time_window,
            "research_questions": payload.research_questions,
            "talking_points": payload.talking_points,
        },
    )
    db.add(job)
    db.commit()
    db.refresh(session)
    db.refresh(job)

    session_response = ResearchSessionResponse.model_validate(session)
    session_response.active_job = ResearchJobResponse.model_validate(job)

    return ResearchSessionCreateResponse(
        session=session_response,
        job=ResearchJobResponse.model_validate(job),
    )


@router.get(
    "",
    response_model=PaginatedResearchSessionsResponse,
    status_code=status.HTTP_200_OK,
    summary="List all research sessions accessible to the current user",
)
def list_research_sessions(
    page: int = Query(1, ge=1, description="Page number starting at 1"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    scope: Optional[OwnershipScope] = Query(None, description="Filter by PERSONAL or WORKSPACE"),
    status_filter: Optional[SessionStatus] = Query(None, alias="status", description="Filter by ACTIVE or ARCHIVED"),
    search: Optional[str] = Query(None, description="Search target name or title"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaginatedResearchSessionsResponse:
    """Retrieve paginated sessions with strict isolation: personal sessions + member workspaces."""
    user_workspace_ids = [
        m.workspace_id
        for m in db.query(WorkspaceMembership.workspace_id)
        .filter(WorkspaceMembership.user_id == current_user.id)
        .all()
    ]

    # Base access filter: owned personally OR belongs to member workspace
    access_condition = or_(
        ResearchSession.owner_user_id == current_user.id,
        ResearchSession.workspace_id.in_(user_workspace_ids) if user_workspace_ids else False,
    )

    query = db.query(ResearchSession).filter(access_condition)

    if scope:
        query = query.filter(ResearchSession.scope == scope)
    if status_filter:
        query = query.filter(ResearchSession.status == status_filter)
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                ResearchSession.title.ilike(term),
                ResearchSession.target_name.ilike(term),
            )
        )

    total = query.count()
    total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 1

    items = (
        query.order_by(ResearchSession.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return PaginatedResearchSessionsResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=[ResearchSessionListItemResponse.model_validate(item) for item in items],
    )


@router.get(
    "/{session_id}",
    response_model=ResearchSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get details of a specific research session",
)
def get_research_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResearchSessionResponse:
    """Retrieve a single research session by ID with authorized access."""
    session = db.query(ResearchSession).filter(ResearchSession.id == session_id).first()
    if not session:
        raise NotFoundException(message="Research session not found.", code="SESSION_NOT_FOUND")

    verify_session_access(session, current_user, db)

    latest_job = (
        db.query(ResearchJob)
        .filter(ResearchJob.session_id == session.id)
        .order_by(ResearchJob.created_at.desc())
        .first()
    )

    response = ResearchSessionResponse.model_validate(session)
    if latest_job:
        response.active_job = ResearchJobResponse.model_validate(latest_job)

    return response


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a research session",
)
def delete_research_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete a research session and its associated jobs and results."""
    session = db.query(ResearchSession).filter(ResearchSession.id == session_id).first()
    if not session:
        raise NotFoundException(message="Research session not found.", code="SESSION_NOT_FOUND")

    verify_session_access(session, current_user, db)

    # For workspace sessions, verify user has administrative role
    if session.scope == OwnershipScope.WORKSPACE:
        membership = (
            db.query(WorkspaceMembership)
            .filter(
                WorkspaceMembership.workspace_id == session.workspace_id,
                WorkspaceMembership.user_id == current_user.id,
            )
            .first()
        )
        if not membership or membership.role not in [WorkspaceRole.OWNER, WorkspaceRole.ADMIN]:
            raise ForbiddenException(
                message="Only workspace administrators can delete workspace research sessions.",
                code="INSUFFICIENT_PERMISSIONS",
            )

    db.delete(session)
    db.commit()


@router.get(
    "/{session_id}/result",
    response_model=ResearchResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Get synthesized intelligence result for a session",
)
def get_research_result(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResearchResultResponse:
    """Retrieve the latest synthesized intelligence result for a research session."""
    session = db.query(ResearchSession).filter(ResearchSession.id == session_id).first()
    if not session:
        raise NotFoundException(message="Research session not found.", code="SESSION_NOT_FOUND")

    verify_session_access(session, current_user, db)

    result = (
        db.query(ResearchResult)
        .filter(ResearchResult.session_id == session_id)
        .order_by(ResearchResult.created_at.desc())
        .first()
    )
    if not result:
        # Check active job status to provide helpful error
        latest_job = (
            db.query(ResearchJob)
            .filter(ResearchJob.session_id == session_id)
            .order_by(ResearchJob.created_at.desc())
            .first()
        )
        job_status = latest_job.status.value if latest_job else "NONE"
        raise NotFoundException(
            message=f"Research results are not yet available for this session. Current job status: {job_status}",
            code="RESULT_NOT_READY",
            details={"session_id": str(session_id), "job_status": job_status},
        )

    return ResearchResultResponse.model_validate(result)


@router.get(
    "/{session_id}/events",
    response_model=EventsListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get extracted events from the latest research result",
)
def get_research_events(
    session_id: uuid.UUID,
    search: Optional[str] = Query(None, description="Search event titles and descriptions"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EventsListResponse:
    """Return key developments and events extracted during research."""
    session = db.query(ResearchSession).filter(ResearchSession.id == session_id).first()
    if not session:
        raise NotFoundException(message="Research session not found.", code="SESSION_NOT_FOUND")

    verify_session_access(session, current_user, db)

    result = (
        db.query(ResearchResult)
        .filter(ResearchResult.session_id == session_id)
        .order_by(ResearchResult.created_at.desc())
        .first()
    )

    if not result or not result.key_developments:
        return EventsListResponse(
            session_id=session.id,
            result_id=result.id if result else None,
            total=0,
            events=[],
        )

    events: List[Dict[str, Any]] = result.key_developments
    if search and search.strip():
        term = search.strip().lower()
        events = [
            e
            for e in events
            if term in str(e.get("title", "")).lower() or term in str(e.get("description", "")).lower()
        ]

    return EventsListResponse(
        session_id=session.id,
        result_id=result.id,
        total=len(events),
        events=events,
    )


@router.get(
    "/{session_id}/claims",
    response_model=ClaimsListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get verified claims and evidence from the latest research result",
)
def get_research_claims(
    session_id: uuid.UUID,
    verification_status: Optional[EvidenceVerificationStatus] = Query(
        None, description="Filter claims by verification status"
    ),
    search: Optional[str] = Query(None, description="Search claim text"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ClaimsListResponse:
    """Return atomic claims and associated evidence assessments from the latest research."""
    session = db.query(ResearchSession).filter(ResearchSession.id == session_id).first()
    if not session:
        raise NotFoundException(message="Research session not found.", code="SESSION_NOT_FOUND")

    verify_session_access(session, current_user, db)

    result = (
        db.query(ResearchResult)
        .filter(ResearchResult.session_id == session_id)
        .order_by(ResearchResult.created_at.desc())
        .first()
    )

    if not result or not result.claims_and_evidence:
        return ClaimsListResponse(
            session_id=session.id,
            result_id=result.id if result else None,
            total=0,
            claims=[],
        )

    claims: List[Dict[str, Any]] = result.claims_and_evidence

    if verification_status:
        target_status = verification_status.value
        claims = [
            c
            for c in claims
            if str(c.get("verification_status", "")).upper() == target_status
            or str(c.get("status", "")).upper() == target_status
        ]

    if search and search.strip():
        term = search.strip().lower()
        claims = [
            c
            for c in claims
            if term in str(c.get("claim", "")).lower() or term in str(c.get("evidence", "")).lower()
        ]

    return ClaimsListResponse(
        session_id=session.id,
        result_id=result.id,
        total=len(claims),
        claims=claims,
    )

