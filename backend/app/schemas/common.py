"""Common response and error schemas."""

from typing import Any, Optional
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Detailed error object matching the shared contract."""

    code: str = Field(..., description="Stable programmatic error code")
    message: str = Field(..., description="Human-readable error description")
    details: Optional[Any] = Field(default_factory=dict, description="Contextual validation or error metadata")


class ApiErrorResponse(BaseModel):
    """Standardized API error response envelope."""

    error: ErrorDetail


class SuccessResponse(BaseModel):
    """Standard success wrapper."""

    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None

