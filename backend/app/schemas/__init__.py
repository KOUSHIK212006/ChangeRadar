"""Pydantic schemas and DTOs."""

from app.schemas.auth import (
    AuthResponse,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.schemas.common import (
    ApiErrorResponse,
    ErrorDetail,
    SuccessResponse,
)
from app.schemas.health import (
    DatabaseHealth,
    HealthResponse,
)
from app.schemas.job import (
    ResearchJobResponse,
)
from app.schemas.research import (
    PaginatedResearchSessionsResponse,
    ResearchSessionCreate,
    ResearchSessionCreateResponse,
    ResearchSessionListItemResponse,
    ResearchSessionResponse,
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
    "ResearchJobResponse",
    "PaginatedResearchSessionsResponse",
    "ResearchSessionCreate",
    "ResearchSessionCreateResponse",
    "ResearchSessionListItemResponse",
    "ResearchSessionResponse",
    "ClaimRecordResponse",
    "ClaimsListResponse",
    "EventRecordResponse",
    "EventsListResponse",
    "ResearchResultResponse",
]
