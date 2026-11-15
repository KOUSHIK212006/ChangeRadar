"""Research sessions and briefing REST endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_optional, get_db
from app.models.enums import OwnershipScope
from app.models.user import User
from app.schemas.research import (
    CreateSessionRequest,
    MarkReviewedResponse,
    ResearchSessionResponse,
    StressTestSubmissionRequest,
)
from app.services import session_service
from intelligence.contracts import DeltaRecord, IntelligenceResult, StressTestResult

router = APIRouter(prefix="/sessions", tags=["Research Sessions"])


@router.get(
    "",
    response_model=List[ResearchSessionResponse],
    summary="List Research Sessions",
    description="Retrieve research sessions filtered by ownership scope (PERSONAL or WORKSPACE).",
)
def list_sessions(
    scope: Optional[OwnershipScope] = Query(None, description="Filter by PERSONAL or WORKSPACE"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
) -> List[ResearchSessionResponse]:
    """List research sessions for the current authenticated user context."""
    return session_service.get_sessions_list(db, scope=scope, user=current_user)


@router.post(
    "",
    response_model=ResearchSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Research Session",
    description="Create a new research session, enqueue the research pipeline, and initialize briefing data.",
)
def create_session(
    payload: CreateSessionRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
) -> ResearchSessionResponse:
    """Create a research session and initiate research investigation."""
    return session_service.create_session_and_job(db, payload, user=current_user)


@router.get(
    "/{session_id}",
    response_model=ResearchSessionResponse,
    summary="Get Research Session Details",
)
def get_session(
    session_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
) -> ResearchSessionResponse:
    """Retrieve full session metadata, current stage, and review baseline."""
    session = session_service.get_session_by_id(db, session_id, user=current_user)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research session '{session_id}' not found.",
        )
    return session


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Research Session",
)
def delete_session(
    session_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
) -> None:
    """Delete a research session and its associated jobs and results."""
    success = session_service.delete_session_by_id(db, session_id, user=current_user)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research session '{session_id}' not found.",
        )


@router.get(
    "/{session_id}/briefing",
    response_model=IntelligenceResult,
    summary="Get Synthesized Research Briefing",
    description="Retrieve full evidence-first intelligence briefing including sources, claims, events, and coverage audit.",
)
def get_briefing(
    session_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
) -> IntelligenceResult:
    """Return the synthesized research briefing for the session."""
    briefing = session_service.get_session_briefing(db, session_id, user=current_user)
    if not briefing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Briefing for session '{session_id}' not found.",
        )
    return briefing


@router.get(
    "/{session_id}/delta",
    response_model=Optional[DeltaRecord],
    summary="Get Personal Delta Briefing",
    description="Retrieve changes detected relative to the user's last reviewed baseline.",
)
def get_delta(
    session_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
) -> Optional[DeltaRecord]:
    """Return delta briefing relative to active review baseline."""
    briefing = session_service.get_session_briefing(db, session_id, user=current_user)
    if not briefing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )
    return briefing.delta


@router.post(
    "/{session_id}/review",
    response_model=MarkReviewedResponse,
    summary="Mark Briefing as Reviewed",
    description="Establish review baseline for this session. Subsequent runs will compute Personal Delta against this point in time.",
)
def mark_reviewed(
    session_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
) -> MarkReviewedResponse:
    """Mark briefing state as reviewed by the user."""
    res = session_service.mark_session_reviewed(db, session_id, user=current_user)
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research session '{session_id}' not found.",
        )
    return res


@router.post(
    "/{session_id}/stress-tests",
    response_model=StressTestResult,
    summary="Stress-Test Talking Points",
    description="Evaluate talking points against extracted evidence, identify contradictions, and provide grounded wording recommendations.",
)
def stress_test_talking_points(
    session_id: str,
    payload: StressTestSubmissionRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
) -> StressTestResult:
    """Execute talking-point stress testing against verified claims."""
    return session_service.execute_stress_test(db, session_id, payload, user=current_user)
