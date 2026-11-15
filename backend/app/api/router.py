"""Root API router combining top-level endpoints and versioned routers."""

from datetime import datetime, timezone
from fastapi import APIRouter

from app.api.v1.router import api_v1_router
from app.config import settings
from app.core.database import check_db_connection, engine
from app.schemas.health import DatabaseHealth, HealthResponse

root_router = APIRouter()


@root_router.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Root Health Check",
    description="High-level health check endpoint for container orchestrators and load balancers.",
)
def root_health() -> HealthResponse:
    """Return application and database health status."""
    db_ok, db_err = check_db_connection()
    db_status = "connected" if db_ok else "unreachable"
    overall_status = "healthy" if db_ok else "degraded"

    return HealthResponse(
        status=overall_status,
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(timezone.utc),
        database=DatabaseHealth(
            status=db_status,
            dialect=engine.dialect.name,
            error=db_err,
        ),
    )


# Mount versioned API routes
root_router.include_router(api_v1_router, prefix=settings.API_V1_STR)

