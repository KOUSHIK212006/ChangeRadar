"""Pytest fixtures and test configuration."""

import os
import sys
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Configure test environment variables before importing app
os.environ["ENVIRONMENT"] = "testing"
os.environ["DEBUG"] = "true"
os.environ["LOG_LEVEL"] = "WARNING"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = "test-only-jwt-secret-key-at-least-32-chars"
os.environ["INTELLIGENCE_FIXTURE_MODE"] = "true"

from app.api.deps import get_db
from app.config import Settings, get_settings
from app.core.database import Base
import app.core.database as db_module
import app.models  # Ensure all SQLAlchemy models are registered
from app.main import app

from sqlalchemy.pool import StaticPool

# Test SQLite in-memory engine with StaticPool so all threads share memory safely
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
db_module.engine = test_engine
db_module.SessionLocal = TestingSessionLocal


def get_test_settings() -> Settings:
    """Override application settings for tests."""
    return Settings(
        ENVIRONMENT="testing",
        DEBUG=True,
        LOG_LEVEL="WARNING",
        DATABASE_URL="sqlite:///:memory:",
        JWT_SECRET_KEY="test-only-jwt-secret-key-at-least-32-chars",
        CORS_ORIGINS=["http://localhost:5173", "http://testserver"],
    )


@pytest.fixture(autouse=True)
def setup_test_db():
    """Create fresh database tables for each test and clean up afterwards."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provide a clean database session for a test."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Provide FastAPI test client with database override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    from app.core.database import get_db as core_get_db
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[core_get_db] = override_get_db
    app.dependency_overrides[get_settings] = get_test_settings

    with TestClient(app, base_url="http://testserver") as test_client:
        yield test_client

    app.dependency_overrides.clear()
