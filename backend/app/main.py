"""Main FastAPI application factory and entrypoint."""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.router import root_router
from app.config import settings
from app.core.handlers import register_exception_handlers
from app.logging_config import setup_logging

logger = logging.getLogger("changeradar")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for structured logging of all incoming HTTP requests and response times."""

    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        client_host = request.client.host if request.client else "unknown"

        logger.info(f"Incoming request: {request.method} {request.url.path} from {client_host}")

        response = await call_next(request)

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            f"Completed request: {request.method} {request.url.path} - "
            f"Status: {response.status_code} - Duration: {duration_ms:.2f}ms"
        )
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle event handler for server startup and shutdown tasks."""
    setup_logging(log_level=settings.LOG_LEVEL)
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} [{settings.ENVIRONMENT}]")
    logger.info(f"CORS allowed origins: {settings.CORS_ORIGINS}")
    logger.info(f"API v1 prefix mounted at: {settings.API_V1_STR}")

    yield

    logger.info(f"Shutting down {settings.APP_NAME}")


def create_app() -> FastAPI:
    """Application factory for FastAPI app initialization."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="ChangeRadar Backend & Platform - AI-powered pre-meeting research intelligence",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # 1. CORS Configuration for React Frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    # 2. Request Logging Middleware
    app.add_middleware(RequestLoggingMiddleware)

    # 3. Centralized Exception Handling
    register_exception_handlers(app)

    # 4. Route Registration
    app.include_router(root_router)

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

