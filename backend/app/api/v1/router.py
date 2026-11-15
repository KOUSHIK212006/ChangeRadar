"""API v1 Router aggregation."""

from fastapi import APIRouter
from app.api.v1 import health, metrics, runs, sessions

api_v1_router = APIRouter()

# Register sub-routers
api_v1_router.include_router(health.router)
api_v1_router.include_router(sessions.router)
api_v1_router.include_router(runs.router)
api_v1_router.include_router(metrics.router)
