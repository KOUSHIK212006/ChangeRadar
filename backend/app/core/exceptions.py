"""Domain and application exceptions for ChangeRadar backend."""

from typing import Any, Optional


class AppException(Exception):
    """Base application exception with standardized error details."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Optional[Any] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundException(AppException):
    """Raised when a requested resource does not exist."""

    def __init__(
        self,
        message: str = "Resource not found",
        code: str = "RESOURCE_NOT_FOUND",
        details: Optional[Any] = None,
    ):
        super().__init__(message=message, code=code, status_code=404, details=details)


class BadRequestException(AppException):
    """Raised when client inputs or requests are malformed or invalid."""

    def __init__(
        self,
        message: str = "Bad request",
        code: str = "BAD_REQUEST",
        details: Optional[Any] = None,
    ):
        super().__init__(message=message, code=code, status_code=400, details=details)


class UnauthorizedException(AppException):
    """Raised when authentication is missing or invalid."""

    def __init__(
        self,
        message: str = "Authentication required",
        code: str = "UNAUTHORIZED",
        details: Optional[Any] = None,
    ):
        super().__init__(message=message, code=code, status_code=401, details=details)


class ForbiddenException(AppException):
    """Raised when authenticated user lacks permission for the requested resource."""

    def __init__(
        self,
        message: str = "Access forbidden",
        code: str = "FORBIDDEN",
        details: Optional[Any] = None,
    ):
        super().__init__(message=message, code=code, status_code=403, details=details)


class ConflictException(AppException):
    """Raised on state conflict, such as duplicate key or version mismatch."""

    def __init__(
        self,
        message: str = "Resource state conflict",
        code: str = "CONFLICT",
        details: Optional[Any] = None,
    ):
        super().__init__(message=message, code=code, status_code=409, details=details)


class ValidationException(AppException):
    """Raised when domain validation fails."""

    def __init__(
        self,
        message: str = "Validation failed",
        code: str = "VALIDATION_ERROR",
        details: Optional[Any] = None,
    ):
        super().__init__(message=message, code=code, status_code=422, details=details)


class DatabaseException(AppException):
    """Raised on database operational errors."""

    def __init__(
        self,
        message: str = "A database error occurred",
        code: str = "DATABASE_ERROR",
        details: Optional[Any] = None,
    ):
        super().__init__(message=message, code=code, status_code=500, details=details)

