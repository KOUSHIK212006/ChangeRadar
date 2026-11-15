"""API v1 Router aggregation."""

from fastapi import APIRouter
from app.api.v1 import auth, health, jobs, research

api_v1_router = APIRouter()

# Register sub-routers
api_v1_router.include_router(health.router)
api_v1_router.include_router(auth.router)
api_v1_router.include_router(research.router)
api_v1_router.include_router(jobs.router)
