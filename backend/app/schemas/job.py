"""Pydantic schemas for durable research job tracking."""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from app.models.enums import ResearchJobStatus


class ResearchJobResponse(BaseModel):
    """Execution status and progress details for a research job."""

    id: uuid.UUID
    session_id: uuid.UUID
    status: ResearchJobStatus
    stage: Optional[str] = None
    progress_percent: int = Field(default=0, ge=0, le=100)
    attempt_count: int
    max_attempts: int
    claimed_at: Optional[datetime] = None
    claimed_by: Optional[str] = None
    heartbeat_at: Optional[datetime] = None
    next_retry_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    parameters: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

