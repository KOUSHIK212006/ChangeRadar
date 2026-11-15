"""Centralized exception handlers for FastAPI."""

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppException

logger = logging.getLogger(__name__)


def build_error_response(code: str, message: str, details: Any = None, status_code: int = 500) -> JSONResponse:
    """Format standard API error response envelope."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details if details is not None else {},
            }
        },
    )


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle custom application exceptions."""
    logger.warning(
        f"AppException on {request.method} {request.url.path}: [{exc.code}] {exc.message} (details={exc.details})"
    )
    return build_error_response(
        code=exc.code,
        message=exc.message,
        details=exc.details,
        status_code=exc.status_code,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic/FastAPI request validation errors."""
    logger.info(f"Validation error on {request.method} {request.url.path}: {exc.errors()}")
    # Format details cleanly
    formatted_errors = []
    for err in exc.errors():
        loc = " -> ".join(str(item) for item in err.get("loc", []))
        formatted_errors.append({
            "field": loc,
            "message": err.get("msg"),
            "type": err.get("type"),
        })

    return build_error_response(
        code="VALIDATION_ERROR",
        message="Request parameter or payload validation failed.",
        details=formatted_errors,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle standard Starlette/FastAPI HTTP exceptions (e.g. 404, 405)."""
    error_code = "HTTP_ERROR"
    if exc.status_code == status.HTTP_404_NOT_FOUND:
        error_code = "NOT_FOUND"
    elif exc.status_code == status.HTTP_405_METHOD_NOT_ALLOWED:
        error_code = "METHOD_NOT_ALLOWED"
    elif exc.status_code == status.HTTP_403_FORBIDDEN:
        error_code = "FORBIDDEN"
    elif exc.status_code == status.HTTP_401_UNAUTHORIZED:
        error_code = "UNAUTHORIZED"

    return build_error_response(
        code=error_code,
        message=str(exc.detail),
        details={},
        status_code=exc.status_code,
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unhandled server exceptions."""
    logger.exception(f"Unhandled server error on {request.method} {request.url.path}: {exc}")
    return build_error_response(
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected server error occurred. Please try again later.",
        details={},
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all centralized exception handlers on the FastAPI app instance."""
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, global_exception_handler)

