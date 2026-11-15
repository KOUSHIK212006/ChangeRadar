"""Tests for CORS configuration."""

from fastapi.testclient import TestClient


def test_cors_preflight_allowed_origin(client: TestClient):
    """Verify that OPTIONS pre-flight from allowed origin returns proper CORS headers."""
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "Content-Type",
    }
    response = client.options("/health", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "GET" in response.headers.get("access-control-allow-methods", "")


def test_cors_simple_request_header(client: TestClient):
    """Verify that GET request with allowed Origin includes Access-Control-Allow-Origin header."""
    headers = {"Origin": "http://localhost:5173"}
    response = client.get("/health", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"

