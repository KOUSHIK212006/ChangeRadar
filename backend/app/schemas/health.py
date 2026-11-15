"""Schemas for health check and diagnostic endpoints."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class DatabaseHealth(BaseModel):
    """Database probe health information."""

    status: str = Field(..., description="Connection status: 'connected' or 'unreachable'")
    dialect: Optional[str] = Field(None, description="Database dialect (e.g., postgresql, sqlite)")
    error: Optional[str] = Field(None, description="Connection error message if probe failed")


class HealthResponse(BaseModel):
    """Comprehensive service health response."""

    status: str = Field(..., description="Overall service status ('healthy' or 'degraded')")
    app_name: str = Field(..., description="Application name")
    version: str = Field(..., description="Application semantic version")
    environment: str = Field(..., description="Runtime environment (development, staging, production)")
    timestamp: datetime = Field(..., description="Current UTC timestamp of the health check")
    database: DatabaseHealth = Field(..., description="Database connectivity probe results")

