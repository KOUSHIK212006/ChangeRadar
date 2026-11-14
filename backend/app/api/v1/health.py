"""Health check endpoint for monitoring, readiness, and liveness probes."""

from datetime import datetime, timezone
from fastapi import APIRouter

from app.config import settings
from app.core.database import check_db_connection, engine
from app.schemas.health import DatabaseHealth, HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service Health Check",
    description="Returns the health status of the application and its database connection.",
)
def get_health() -> HealthResponse:
    """Perform health and readiness probe."""
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

