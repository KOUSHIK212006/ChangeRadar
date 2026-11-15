"""Dashboard aggregate metrics endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.research import DashboardMetricsResponse
from app.services import session_service

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get(
    "/dashboard",
    response_model=DashboardMetricsResponse,
    summary="Get Dashboard Metrics",
    description="Aggregate counts of total sessions, newly detected developments, supported claims, and coverage gaps.",
)
def get_dashboard_metrics(db: Session = Depends(get_db)) -> DashboardMetricsResponse:
    """Return dashboard analytics metrics."""
    return session_service.get_dashboard_metrics(db)
