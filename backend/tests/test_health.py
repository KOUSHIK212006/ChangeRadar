"""Tests for root and v1 health check endpoints."""

from fastapi.testclient import TestClient


def test_root_health_check(client: TestClient):
    """Verify that root GET /health returns 200 and expected health metadata."""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert "status" in data
    assert "app_name" in data
    assert "version" in data
    assert "environment" in data
    assert "timestamp" in data
    assert "database" in data
    assert "status" in data["database"]


def test_v1_health_check(client: TestClient):
    """Verify that versioned GET /api/v1/health returns 200 and expected schema."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    data = response.json()
    assert "status" in data
    assert "version" in data
    assert data["database"]["status"] in ["connected", "unreachable"]

