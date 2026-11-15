"""Pydantic schemas and DTOs."""

from app.schemas.auth import (
    AuthResponse,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.schemas.common import ApiErrorResponse, ErrorDetail, SuccessResponse
from app.schemas.health import DatabaseHealth, HealthResponse
from app.schemas.job import ResearchJobResponse as PlatformResearchJobResponse
from app.schemas.research import (
    CreateSessionRequest,
    DashboardMetricsResponse,
    MarkReviewedResponse,
    PaginatedResearchSessionsResponse,
    PlatformResearchSessionResponse,
    ResearchJobResponse,
    ResearchSessionCreate,
    ResearchSessionCreateResponse,
    ResearchSessionListItemResponse,
    ResearchSessionResponse,
    StressTestSubmissionRequest,
)
from app.schemas.result import (
    ClaimRecordResponse,
    ClaimsListResponse,
    EventRecordResponse,
    EventsListResponse,
    ResearchResultResponse,
)

__all__ = [
    "AuthResponse",
    "TokenResponse",
    "UserLoginRequest",
    "UserRegisterRequest",
    "UserResponse",
    "ApiErrorResponse",
    "ErrorDetail",
    "SuccessResponse",
    "DatabaseHealth",
    "HealthResponse",
    "CreateSessionRequest",
    "DashboardMetricsResponse",
    "MarkReviewedResponse",
    "ResearchJobResponse",
    "StressTestSubmissionRequest",
    "ResearchSessionResponse",
    "PlatformResearchJobResponse",
    "PlatformResearchSessionResponse",
    "ResearchSessionCreate",
    "ResearchSessionCreateResponse",
    "ResearchSessionListItemResponse",
    "PaginatedResearchSessionsResponse",
    "ClaimRecordResponse",
    "ClaimsListResponse",
    "EventRecordResponse",
    "EventsListResponse",
    "ResearchResultResponse",
]
