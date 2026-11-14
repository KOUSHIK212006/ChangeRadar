"""Tests for centralized exception handling and error envelope standardization."""

from fastapi.testclient import TestClient

from app.core.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
    UnauthorizedException,
)
from app.main import app


def test_404_not_found_standard_envelope(client: TestClient):
    """Verify that accessing an unknown route returns standard error JSON."""
    response = client.get("/api/v1/non-existent-endpoint")
    assert response.status_code == 404

    data = response.json()
    assert "error" in data
    assert "code" in data["error"]
    assert "message" in data["error"]
    assert data["error"]["code"] == "NOT_FOUND"


def test_405_method_not_allowed_standard_envelope(client: TestClient):
    """Verify that invalid HTTP methods return standardized 405 response."""
    response = client.post("/health")
    assert response.status_code == 405

    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "METHOD_NOT_ALLOWED"


def test_custom_app_exceptions_handling():
    """Verify custom AppException subclasses produce correct HTTP status and code."""
    # Temporarily add test routes raising custom exceptions
    @app.get("/test/custom-not-found")
    def raise_not_found():
        raise NotFoundException("Custom resource missing", code="ITEM_NOT_FOUND")

    @app.get("/test/custom-bad-request")
    def raise_bad_request():
        raise BadRequestException("Invalid parameter supplied", code="INVALID_PARAM")

    @app.get("/test/custom-unauthorized")
    def raise_unauthorized():
        raise UnauthorizedException("Token has expired", code="TOKEN_EXPIRED")

    @app.get("/test/custom-forbidden")
    def raise_forbidden():
        raise ForbiddenException("Insufficient permissions", code="ACCESS_DENIED")

    with TestClient(app) as test_client:
        # Test NotFound
        r = test_client.get("/test/custom-not-found")
        assert r.status_code == 404
        assert r.json()["error"]["code"] == "ITEM_NOT_FOUND"
        assert r.json()["error"]["message"] == "Custom resource missing"

        # Test BadRequest
        r = test_client.get("/test/custom-bad-request")
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "INVALID_PARAM"

        # Test Unauthorized
        r = test_client.get("/test/custom-unauthorized")
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "TOKEN_EXPIRED"

        # Test Forbidden
        r = test_client.get("/test/custom-forbidden")
        assert r.status_code == 403
        assert r.json()["error"]["code"] == "ACCESS_DENIED"

