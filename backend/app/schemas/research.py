"""Pydantic schemas for research sessions."""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.enums import OwnershipScope, SessionStatus
from app.schemas.job import ResearchJobResponse


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


class ResearchSessionResponse(BaseModel):
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
    active_job: Optional[ResearchJobResponse] = None

    model_config = {"from_attributes": True}


class ResearchSessionCreateResponse(BaseModel):
    """Response returned upon successful creation of a research session and queued job."""

    session_id: uuid.UUID
    job_id: uuid.UUID
    session: ResearchSessionResponse
    job: ResearchJobResponse


class PaginatedResearchSessionsResponse(BaseModel):
    """Paginated list of research sessions."""

    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[ResearchSessionListItemResponse]

