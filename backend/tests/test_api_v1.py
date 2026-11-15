"""Comprehensive tests for ChangeRadar REST APIs under /api/v1."""

import uuid
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.enums import EvidenceVerificationStatus, OwnershipScope, ResearchJobStatus, ResearchResultStatus
from app.models.research_job import ResearchJob
from app.models.research_result import ResearchResult
from app.models.research_session import ResearchSession
from app.models.user import User


# Helper functions to seed users and generate auth headers
def create_test_user(db: Session, email: str, password: str = "password123", full_name: str = "Test User") -> User:
    user = User(
        email=email.lower(),
        hashed_password=get_password_hash(password),
        full_name=full_name,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_auth_headers(client: TestClient, email: str = "user@changeradar.ai", password: str = "password123") -> dict:
    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    token = login_resp.json()["token"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# 1. AUTH TESTS
# ==============================================================================

def test_auth_register_success(client: TestClient):
    """Verify that a user can register and receive a valid JWT token."""
    payload = {
        "email": "newuser@changeradar.ai",
        "password": "securepassword123",
        "full_name": "New Researcher",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert "user" in data
    assert data["user"]["email"] == "newuser@changeradar.ai"
    assert data["user"]["full_name"] == "New Researcher"
    assert "token" in data
    assert "access_token" in data["token"]
    assert data["token"]["token_type"] == "bearer"


def test_auth_register_duplicate_email_conflict(client: TestClient, db_session: Session):
    """Verify registration fails with 409 Conflict if email is already taken."""
    create_test_user(db_session, "duplicate@changeradar.ai")

    payload = {
        "email": "duplicate@changeradar.ai",
        "password": "securepassword123",
        "full_name": "Another User",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "USER_ALREADY_EXISTS"


def test_auth_login_success(client: TestClient, db_session: Session):
    """Verify login with valid credentials returns user profile and access token."""
    create_test_user(db_session, "loginuser@changeradar.ai", "correctpass123")

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "loginuser@changeradar.ai", "password": "correctpass123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["email"] == "loginuser@changeradar.ai"
    assert "access_token" in data["token"]


def test_auth_login_invalid_password(client: TestClient, db_session: Session):
    """Verify login fails with 401 Unauthorized when password is wrong."""
    create_test_user(db_session, "wrongpass@changeradar.ai", "correctpass123")

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "wrongpass@changeradar.ai", "password": "wrongpassword!"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_auth_me_endpoint(client: TestClient, db_session: Session):
    """Verify GET /auth/me returns current user profile when authenticated."""
    create_test_user(db_session, "me@changeradar.ai", "password123", "Me Analyst")
    headers = get_auth_headers(client, "me@changeradar.ai", "password123")

    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@changeradar.ai"
    assert data["full_name"] == "Me Analyst"


def test_auth_me_unauthorized_without_token(client: TestClient):
    """Verify GET /auth/me rejects requests without token with 401."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"


# ==============================================================================
# 2. RESEARCH SESSIONS TESTS
# ==============================================================================

def test_create_personal_research_session(client: TestClient, db_session: Session):
    """Verify POST /research creates a session and queues a worker job."""
    create_test_user(db_session, "researcher1@changeradar.ai", "password123")
    headers = get_auth_headers(client, "researcher1@changeradar.ai", "password123")

    payload = {
        "title": "Stripe APAC Expansion Analysis",
        "target_name": "Stripe",
        "target_type": "company",
        "meeting_context": "Partnership prep meeting",
        "time_window": "past_30_days",
        "research_questions": ["What is Stripe's latest valuation?"],
        "talking_points": ["Stripe expanded in Singapore."],
        "scope": "PERSONAL",
    }

    response = client.post("/api/v1/research", json=payload, headers=headers)
    assert response.status_code == 201

    data = response.json()
    assert "session" in data
    assert data["session"]["target_name"] == "Stripe"
    assert data["session"]["scope"] == "PERSONAL"
    assert "job" in data
    assert data["job"]["status"] == "QUEUED"
    assert data["job"]["attempt_count"] == 0


def test_list_research_sessions_pagination_and_isolation(client: TestClient, db_session: Session):
    """Verify GET /research returns paginated sessions and enforces user isolation."""
    user_a = create_test_user(db_session, "usera@changeradar.ai", "password123")
    user_b = create_test_user(db_session, "userb@changeradar.ai", "password123")

    # Create 3 sessions for User A
    for i in range(3):
        session = ResearchSession(
            title=f"User A Session {i}",
            target_name=f"Company A{i}",
            owner_user_id=user_a.id,
            scope=OwnershipScope.PERSONAL,
        )
        db_session.add(session)

    # Create 2 sessions for User B
    for i in range(2):
        session = ResearchSession(
            title=f"User B Session {i}",
            target_name=f"Company B{i}",
            owner_user_id=user_b.id,
            scope=OwnershipScope.PERSONAL,
        )
        db_session.add(session)
    db_session.commit()

    headers_a = get_auth_headers(client, "usera@changeradar.ai", "password123")

    # User A lists sessions: should only see 3 items
    response = client.get("/api/v1/research?page=1&page_size=10", headers=headers_a)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3
    for item in data["items"]:
        assert "User A Session" in item["title"]


def test_get_research_session_by_id(client: TestClient, db_session: Session):
    """Verify GET /research/{id} retrieves the detailed session with its active job."""
    user = create_test_user(db_session, "detail@changeradar.ai", "password123")
    headers = get_auth_headers(client, "detail@changeradar.ai", "password123")

    session = ResearchSession(
        title="Detail Test",
        target_name="Acme Corp",
        owner_user_id=user.id,
        scope=OwnershipScope.PERSONAL,
    )
    db_session.add(session)
    db_session.commit()

    job = ResearchJob(
        session_id=session.id,
        status=ResearchJobStatus.RUNNING,
        stage="searching",
        progress_percent=45,
    )
    db_session.add(job)
    db_session.commit()

    response = client.get(f"/api/v1/research/{session.id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(session.id)
    assert data["active_job"] is not None
    assert data["active_job"]["status"] == "RUNNING"
    assert data["active_job"]["progress_percent"] == 45


def test_delete_research_session(client: TestClient, db_session: Session):
    """Verify DELETE /research/{id} deletes the session and returns 204."""
    user = create_test_user(db_session, "del@changeradar.ai", "password123")
    headers = get_auth_headers(client, "del@changeradar.ai", "password123")

    session = ResearchSession(
        title="To Delete",
        target_name="Doomed Target",
        owner_user_id=user.id,
        scope=OwnershipScope.PERSONAL,
    )
    db_session.add(session)
    db_session.commit()

    response = client.delete(f"/api/v1/research/{session.id}", headers=headers)
    assert response.status_code == 204

    # Verify session is gone
    get_resp = client.get(f"/api/v1/research/{session.id}", headers=headers)
    assert get_resp.status_code == 404


def test_unauthorized_user_cannot_access_other_personal_session(client: TestClient, db_session: Session):
    """Verify User B cannot read or delete User A's personal research session."""
    user_a = create_test_user(db_session, "alice@changeradar.ai", "password123")
    user_b = create_test_user(db_session, "bob@changeradar.ai", "password123")

    session_a = ResearchSession(
        title="Alice's Private Pitch",
        target_name="Target Alpha",
        owner_user_id=user_a.id,
        scope=OwnershipScope.PERSONAL,
    )
    db_session.add(session_a)
    db_session.commit()

    headers_b = get_auth_headers(client, "bob@changeradar.ai", "password123")

    # Bob tries to read Alice's session -> 404
    resp = client.get(f"/api/v1/research/{session_a.id}", headers=headers_b)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "SESSION_NOT_FOUND"

    # Bob tries to delete Alice's session -> 404
    del_resp = client.delete(f"/api/v1/research/{session_a.id}", headers=headers_b)
    assert del_resp.status_code == 404


# ==============================================================================
# 3. RESEARCH RESULTS, EVENTS, AND CLAIMS TESTS
# ==============================================================================

def test_get_research_result_when_ready(client: TestClient, db_session: Session):
    """Verify GET /research/{id}/result returns synthesized briefing."""
    user = create_test_user(db_session, "resultuser@changeradar.ai", "password123")
    headers = get_auth_headers(client, "resultuser@changeradar.ai", "password123")

    session = ResearchSession(
        title="Result Test",
        target_name="Alpha Tech",
        owner_user_id=user.id,
    )
    db_session.add(session)
    db_session.commit()

    result = ResearchResult(
        session_id=session.id,
        research_status=ResearchResultStatus.COMPLETED,
        summary="Alpha Tech launched AI chip.",
        key_developments=[
            {"id": "ev-1", "title": "AI Chip Launch", "description": "3nm custom silicon"}
        ],
        claims_and_evidence=[
            {
                "claim": "Chip delivers 4x inference speed",
                "verification_status": EvidenceVerificationStatus.SUPPORTED.value,
                "evidence": "Benchmark publication confirmed",
            }
        ],
        coverage_report={"searches_executed": 5},
    )
    db_session.add(result)
    db_session.commit()

    response = client.get(f"/api/v1/research/{session.id}/result", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["summary"] == "Alpha Tech launched AI chip."
    assert data["research_status"] == "COMPLETED"
    assert len(data["key_developments"]) == 1


def test_get_research_events_and_claims(client: TestClient, db_session: Session):
    """Verify GET /research/{id}/events and /claims return filtered lists."""
    user = create_test_user(db_session, "eventsclaims@changeradar.ai", "password123")
    headers = get_auth_headers(client, "eventsclaims@changeradar.ai", "password123")

    session = ResearchSession(
        title="Events & Claims",
        target_name="Fintech Corp",
        owner_user_id=user.id,
    )
    db_session.add(session)
    db_session.commit()

    result = ResearchResult(
        session_id=session.id,
        research_status=ResearchResultStatus.COMPLETED,
        key_developments=[
            {"id": "ev-1", "title": "Acquired PayFast", "description": "Payment gateway acquisition"},
            {"id": "ev-2", "title": "Q3 Results Released", "description": "Record profit"},
        ],
        claims_and_evidence=[
            {
                "claim": "Fintech Corp revenue grew 25%",
                "verification_status": "SUPPORTED",
                "evidence": "SEC 10-Q filing",
            },
            {
                "claim": "CEO plans to step down in December",
                "verification_status": "CONTRADICTED",
                "evidence": "Official press denial",
            },
        ],
    )
    db_session.add(result)
    db_session.commit()

    # 1. Events list with search
    events_resp = client.get(f"/api/v1/research/{session.id}/events?search=payfast", headers=headers)
    assert events_resp.status_code == 200
    events_data = events_resp.json()
    assert events_data["total"] == 1
    assert events_data["events"][0]["title"] == "Acquired PayFast"

    # 2. Claims list with verification status filter
    claims_resp = client.get(
        f"/api/v1/research/{session.id}/claims?verification_status=CONTRADICTED",
        headers=headers,
    )
    assert claims_resp.status_code == 200
    claims_data = claims_resp.json()
    assert claims_data["total"] == 1
    assert "CEO plans to step down" in claims_data["claims"][0]["claim"]


# ==============================================================================
# 4. JOBS TESTS
# ==============================================================================

def test_get_job_endpoint(client: TestClient, db_session: Session):
    """Verify GET /jobs/{job_id} retrieves job details."""
    user = create_test_user(db_session, "jobuser@changeradar.ai", "password123")
    headers = get_auth_headers(client, "jobuser@changeradar.ai", "password123")

    session = ResearchSession(
        title="Job Endpoint Test",
        target_name="RoboCorp",
        owner_user_id=user.id,
    )
    db_session.add(session)
    db_session.commit()

    job = ResearchJob(
        session_id=session.id,
        status=ResearchJobStatus.RUNNING,
        stage="synthesizing",
        progress_percent=75,
        attempt_count=1,
    )
    db_session.add(job)
    db_session.commit()

    response = client.get(f"/api/v1/jobs/{job.id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(job.id)
    assert data["status"] == "RUNNING"
    assert data["stage"] == "synthesizing"
    assert data["progress_percent"] == 75
    assert data["attempt_count"] == 1


def test_get_job_not_found(client: TestClient, db_session: Session):
    """Verify GET /jobs/{job_id} returns 404 for non-existent job."""
    create_test_user(db_session, "randomuser@changeradar.ai", "password123")
    headers = get_auth_headers(client, "randomuser@changeradar.ai", "password123")

    random_id = uuid.uuid4()
    response = client.get(f"/api/v1/jobs/{random_id}", headers=headers)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "JOB_NOT_FOUND"

