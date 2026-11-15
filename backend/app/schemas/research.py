"""Research schemas for the frontend-facing API and authenticated platform routes.

Bridges the SQLAlchemy persistence layer (Krishank), the intelligence contracts
(Surjith), and the frontend API consumer (Koushik).
"""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import OwnershipScope, SessionStatus
from app.schemas.job import ResearchJobResponse as PlatformResearchJobResponse
from intelligence.contracts import (
    IntelligenceResult,
)


class ResearchJobResponse(BaseModel):
    """Execution status and progress of a research job."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique job identifier")
    session_id: str = Field(..., description="Parent session identifier")
    status: str = Field(..., description="ResearchJobStatus: QUEUED | RUNNING | COMPLETED | etc.")
    current_stage: str = Field("REQUEST_ACCEPTED", description="Current pipeline execution stage")
    progress_pct: int = Field(0, ge=0, le=100, description="Completion percentage")
    attempt_count: int = Field(1, description="Number of execution attempts")
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CreateSessionRequest(BaseModel):
    """Payload for creating a new research session and initiating research."""

    target_name: str = Field(..., min_length=1, max_length=255, description="Entity or topic to research")
    target_type: Optional[str] = Field("company", description="company | person | topic | competitor")
    meeting_context: Optional[str] = Field("", description="Meeting objective and context")
    time_window_days: Optional[int] = Field(30, ge=1, le=365, description="Search lookback window in days")
    research_questions: Optional[List[str]] = Field(default_factory=list, description="Specific research questions")
    talking_points: Optional[List[str]] = Field(default_factory=list, description="Planned talking points to evaluate")
    scope: OwnershipScope = Field(OwnershipScope.PERSONAL, description="PERSONAL or WORKSPACE ownership")
    workspace_id: Optional[str] = Field(None, description="Required if scope is WORKSPACE")
    baseline_session_id: Optional[str] = Field(None, description="Previous session to compute delta against")


class ResearchSessionResponse(BaseModel):
    """Detailed research session representation including latest job and intelligence."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    target_name: str
    target_type: Optional[str] = "company"
    meeting_context: Optional[str] = ""
    time_window_days: int = 30
    research_questions: List[str] = Field(default_factory=list)
    talking_points: List[str] = Field(default_factory=list)
    scope: str = "PERSONAL"
    owner_user_id: Optional[str] = None
    workspace_id: Optional[str] = None
    status: str = "ACTIVE"
    last_reviewed_at: Optional[datetime] = None
    last_reviewed_result_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    latest_job: Optional[ResearchJobResponse] = None
    latest_result: Optional[IntelligenceResult] = None


class StressTestSubmissionRequest(BaseModel):
    """Payload for submitting talking points to be stress-tested."""

    talking_points: List[str] = Field(..., min_length=1, description="List of talking points to stress-test")


class MarkReviewedResponse(BaseModel):
    """Response returned upon marking a research briefing as reviewed."""

    success: bool = True
    reviewed_at: datetime
    session_id: str
    baseline_result_id: Optional[str] = None


class DashboardMetricsResponse(BaseModel):
    """Aggregated portfolio metrics for the user dashboard."""

    totalSessions: int
    newDevelopments: int
    supportedClaims: int
    evidenceGaps: int
    isMockData: bool = False


class ResearchSessionCreate(BaseModel):
    """Payload to initiate a new research session."""

    title: Optional[str] = Field(None, max_length=255, description="Session title. Defaults to target name.")
    target_name: str = Field(..., min_length=1, max_length=255, description="Target entity or topic name")
    target_type: Optional[str] = Field(None, max_length=100, description="Target category: company, person, market, etc.")
    meeting_context: Optional[str] = Field(None, description="Context, meeting goal, or research objective")
    time_window: Optional[str] = Field("past_30_days", max_length=100, description="Time window for news and disclosures")
    research_questions: Optional[List[str]] = Field(default_factory=list, description="Specific questions to answer")
    talking_points: Optional[List[str]] = Field(default_factory=list, description="User's planned talking points to verify")
    scope: OwnershipScope = Field(default=OwnershipScope.PERSONAL, description="Ownership scope (PERSONAL or WORKSPACE)")
    workspace_id: Optional[uuid.UUID] = Field(None, description="Required only when scope is WORKSPACE")


class ResearchSessionListItemResponse(BaseModel):
    """Summarized session representation for list views."""

    id: uuid.UUID
    title: str
    target_name: str
    target_type: Optional[str] = None
    scope: OwnershipScope
    owner_user_id: Optional[uuid.UUID] = None
    workspace_id: Optional[uuid.UUID] = None
    status: SessionStatus
    last_reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PlatformResearchSessionResponse(BaseModel):
    """Detailed research session representation including latest job info."""

    id: uuid.UUID
    title: str
    target_name: str
    target_type: Optional[str] = None
    meeting_context: Optional[str] = None
    time_window: Optional[str] = None
    research_questions: Optional[List[str]] = None
    talking_points: Optional[List[str]] = None
    scope: OwnershipScope
    owner_user_id: Optional[uuid.UUID] = None
    workspace_id: Optional[uuid.UUID] = None
    status: SessionStatus
    last_reviewed_at: Optional[datetime] = None
    last_reviewed_result_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime
    active_job: Optional[PlatformResearchJobResponse] = None

    model_config = {"from_attributes": True}


class ResearchSessionCreateResponse(BaseModel):
    """Response returned upon successful creation of a research session and queued job."""

    session_id: uuid.UUID
    job_id: uuid.UUID
    session: PlatformResearchSessionResponse
    job: PlatformResearchJobResponse


class PaginatedResearchSessionsResponse(BaseModel):
    """Paginated list of research sessions."""

    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[ResearchSessionListItemResponse]
