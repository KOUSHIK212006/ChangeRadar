"""Pydantic schemas for research results, briefings, events, and claims."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.models.enums import EvidenceVerificationStatus, ResearchResultStatus


class ResearchResultResponse(BaseModel):
    """Full synthesized research result and briefing."""

    id: uuid.UUID
    session_id: uuid.UUID
    job_id: Optional[uuid.UUID] = None
    baseline_result_id: Optional[uuid.UUID] = None
    research_status: ResearchResultStatus
    summary: Optional[str] = None
    key_developments: Optional[List[Dict[str, Any]]] = None
    sources: Optional[List[Dict[str, Any]]] = None
    claims_and_evidence: Optional[List[Dict[str, Any]]] = None
    coverage_report: Optional[Dict[str, Any]] = None
    talking_points_analysis: Optional[List[Dict[str, Any]]] = None
    is_delta: bool = False
    delta_summary: Optional[Dict[str, Any]] = None
    is_reviewed: bool = False
    reviewed_at: Optional[datetime] = None
    reviewed_by_user_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EventRecordResponse(BaseModel):
    """Individual event/development extracted from research."""

    id: Optional[str] = None
    title: str
    description: Optional[str] = None
    event_date: Optional[str] = None
    status: Optional[str] = None
    confidence: Optional[float] = None
    sources: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None


class EventsListResponse(BaseModel):
    """Container for events extracted from research."""

    session_id: uuid.UUID
    result_id: Optional[uuid.UUID] = None
    total: int
    events: List[Dict[str, Any]]


class ClaimRecordResponse(BaseModel):
    """Atomic claim and its evidence verification status."""

    id: Optional[str] = None
    claim: str
    verification_status: EvidenceVerificationStatus
    rationale: Optional[str] = None
    evidence: Optional[str] = None
    sources: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None


class ClaimsListResponse(BaseModel):
    """Container for claims and evidence assessments."""

    session_id: uuid.UUID
    result_id: Optional[uuid.UUID] = None
    total: int
    claims: List[Dict[str, Any]]
