"""Comprehensive Privacy, Ownership, and Authorization Test Suite (Phase 6).

Covers:
1. Owner accessing their own research (Personal & Workspace).
2. Another user attempting to access private research (returns 404/SESSION_NOT_FOUND to prevent ID enumeration).
3. Unauthorized report / briefing access (returns 404).
4. Unauthorized job access via /runs/{job_id} and /jobs/{job_id} (returns 404).
5. Workspace member access across roles (Owner, Admin, Member - authorized).
6. Non-member workspace access (forbidden or 404).
7. Missing or invalid authentication token (401 NOT_AUTHENTICATED / INVALID_TOKEN).
8. IDOR attempts (manipulating session_id and job_id across tenants).
9. Tenant isolation and leak prevention during session listing.
10. Demo mode boundaries (cannot access private user sessions).
"""

import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Ensure backend directory is in sys.path for direct script execution
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Ensure testing environment variables are set when executed independently
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "test-only-jwt-secret-key-at-least-32-chars")
os.environ.setdefault("INTELLIGENCE_FIXTURE_MODE", "true")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.enums import OwnershipScope, ResearchJobStatus, ResearchResultStatus, SessionStatus, WorkspaceRole
from app.models.research_job import ResearchJob
from app.models.research_result import ResearchResult
from app.models.research_session import ResearchSession
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMembership


def create_user(db: Session, email: str) -> User:
    """Helper to create an active test user with a hashed password."""
    user = User(
        email=email.lower(),
        hashed_password=get_password_hash("password123"),
        full_name=f"User {email}",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_headers(client: TestClient, email: str) -> dict:
    """Helper to authenticate a test user and obtain Bearer authorization headers."""
    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    token = login_resp.json()["token"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_owner_accessing_own_personal_research(client: TestClient, db_session: Session):
    """Verify owner can create, list, retrieve, access briefings, and delete their own personal research session."""
    alice = create_user(db_session, "alice_privacy@changeradar.ai")
    headers_alice = get_headers(client, "alice_privacy@changeradar.ai")

    # 1. Create personal session
    resp = client.post(
        "/api/v1/sessions",
        json={
            "target_name": "Alice Private Target",
            "target_type": "company",
            "meeting_context": "Confidential diligence",
            "scope": "PERSONAL",
        },
        headers=headers_alice,
    )
    assert resp.status_code == 201
    sess_id = resp.json()["id"]

    # 2. Owner can read session
    get_resp = client.get(f"/api/v1/sessions/{sess_id}", headers=headers_alice)
    assert get_resp.status_code == 200
    assert get_resp.json()["target_name"] == "Alice Private Target"

    # 3. Owner can access briefing
    brief_resp = client.get(f"/api/v1/sessions/{sess_id}/briefing", headers=headers_alice)
    assert brief_resp.status_code == 200

    # 4. Owner can delete session
    del_resp = client.delete(f"/api/v1/sessions/{sess_id}", headers=headers_alice)
    assert del_resp.status_code == 204

    # 5. Session is gone after deletion
    post_del_resp = client.get(f"/api/v1/sessions/{sess_id}", headers=headers_alice)
    assert post_del_resp.status_code == 404


def test_unauthorized_user_cannot_access_private_personal_research(client: TestClient, db_session: Session):
    """Verify User B receives 404 when attempting to access User A's private personal research."""
    alice = create_user(db_session, "alice_idor@changeradar.ai")
    bob = create_user(db_session, "bob_idor@changeradar.ai")
    headers_bob = get_headers(client, "bob_idor@changeradar.ai")

    # Seed Alice's private session, job, and result
    now = datetime.now(timezone.utc)
    sess_a = ResearchSession(
        id=uuid.uuid4(),
        title="Alice Confidential Mergers",
        target_name="Acquisition Target X",
        scope=OwnershipScope.PERSONAL,
        owner_user_id=alice.id,
        status=SessionStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    job_a = ResearchJob(
        id=uuid.uuid4(),
        session_id=sess_a.id,
        status=ResearchJobStatus.COMPLETED,
        stage="COMPLETE",
        progress_percent=100,
        created_at=now,
        updated_at=now,
    )
    res_a = ResearchResult(
        id=uuid.uuid4(),
        session_id=sess_a.id,
        job_id=job_a.id,
        research_status=ResearchResultStatus.COMPLETED,
        summary="Classified merger evaluation",
        key_developments=[],
        sources=[],
        claims_and_evidence=[],
        coverage_report={"planned_searches": 1, "executed_searches": 1, "failed_searches": 0, "time_window_days": 30, "origin_diversity_score": 1.0},
        raw_intelligence={"session_id": str(sess_a.id), "job_id": str(job_a.id), "status": "COMPLETED", "coverage": {"planned_searches": 1, "executed_searches": 1, "failed_searches": 0, "time_window_days": 30, "origin_diversity_score": 1.0}},
        created_at=now,
        updated_at=now,
    )
    db_session.add_all([sess_a, job_a, res_a])
    db_session.commit()

    # Bob attempts IDOR on /sessions/{id}
    idor_session = client.get(f"/api/v1/sessions/{sess_a.id}", headers=headers_bob)
    assert idor_session.status_code == 404

    # Bob attempts IDOR on /sessions/{id}/briefing
    idor_briefing = client.get(f"/api/v1/sessions/{sess_a.id}/briefing", headers=headers_bob)
    assert idor_briefing.status_code == 404

    # Bob attempts IDOR on /sessions/{id}/delta
    idor_delta = client.get(f"/api/v1/sessions/{sess_a.id}/delta", headers=headers_bob)
    assert idor_delta.status_code == 404

    # Bob attempts IDOR on /sessions/{id}/review
    idor_review = client.post(f"/api/v1/sessions/{sess_a.id}/review", json={"notes": "Hacked"}, headers=headers_bob)
    assert idor_review.status_code == 404

    # Bob attempts IDOR on /sessions/{id}/stress-tests
    idor_stress = client.post(f"/api/v1/sessions/{sess_a.id}/stress-tests", json={"talking_points": ["fake"]}, headers=headers_bob)
    assert idor_stress.status_code == 404

    # Bob attempts IDOR on /runs/{job_id}
    idor_run = client.get(f"/api/v1/runs/{job_a.id}", headers=headers_bob)
    assert idor_run.status_code == 404

    # Bob attempts IDOR on /jobs/{job_id}
    idor_job = client.get(f"/api/v1/jobs/{job_a.id}", headers=headers_bob)
    assert idor_job.status_code == 404

    # Bob attempts IDOR delete on /sessions/{id}
    idor_delete = client.delete(f"/api/v1/sessions/{sess_a.id}", headers=headers_bob)
    assert idor_delete.status_code == 404


def test_workspace_membership_authorization(client: TestClient, db_session: Session):
    """Verify workspace members have access across roles and non-members are rejected."""
    alice = create_user(db_session, "alice_ws@changeradar.ai")
    bob = create_user(db_session, "bob_ws@changeradar.ai")
    dan_admin = create_user(db_session, "dan_admin_ws@changeradar.ai")
    stranger = create_user(db_session, "stranger_ws@changeradar.ai")

    headers_alice = get_headers(client, "alice_ws@changeradar.ai")
    headers_bob = get_headers(client, "bob_ws@changeradar.ai")
    headers_dan = get_headers(client, "dan_admin_ws@changeradar.ai")
    headers_stranger = get_headers(client, "stranger_ws@changeradar.ai")

    # Create workspace
    now = datetime.now(timezone.utc)
    ws = Workspace(
        id=uuid.uuid4(),
        name="Healthcare Investment Group",
        slug="healthcare-inv",
        created_by_user_id=alice.id,
        created_at=now,
        updated_at=now,
    )
    # Alice is Owner, Dan is Admin, Bob is Member
    m_alice = WorkspaceMembership(workspace_id=ws.id, user_id=alice.id, role=WorkspaceRole.OWNER, created_at=now, updated_at=now)
    m_dan = WorkspaceMembership(workspace_id=ws.id, user_id=dan_admin.id, role=WorkspaceRole.ADMIN, created_at=now, updated_at=now)
    m_bob = WorkspaceMembership(workspace_id=ws.id, user_id=bob.id, role=WorkspaceRole.MEMBER, created_at=now, updated_at=now)
    db_session.add_all([ws, m_alice, m_dan, m_bob])
    db_session.commit()

    # Alice creates a workspace session
    ws_sess = client.post(
        "/api/v1/sessions",
        json={
            "target_name": "BioHealth Corp",
            "target_type": "company",
            "meeting_context": "Joint syndicate meeting",
            "scope": "WORKSPACE",
            "workspace_id": str(ws.id),
        },
        headers=headers_alice,
    )
    assert ws_sess.status_code == 201
    ws_sess_id = ws_sess.json()["id"]

    # Bob (member) can access workspace session
    bob_view = client.get(f"/api/v1/sessions/{ws_sess_id}", headers=headers_bob)
    assert bob_view.status_code == 200
    assert bob_view.json()["target_name"] == "BioHealth Corp"

    # Dan (admin) can access workspace session
    dan_view = client.get(f"/api/v1/sessions/{ws_sess_id}", headers=headers_dan)
    assert dan_view.status_code == 200
    assert dan_view.json()["target_name"] == "BioHealth Corp"

    # Stranger (non-member) cannot access workspace session -> 404
    stranger_view = client.get(f"/api/v1/sessions/{ws_sess_id}", headers=headers_stranger)
    assert stranger_view.status_code == 404

    # Unauthenticated caller cannot access workspace session -> 404
    unauth_ws_view = client.get(f"/api/v1/sessions/{ws_sess_id}")
    assert unauth_ws_view.status_code == 404

    # Stranger cannot create session in Alice's workspace -> 403
    stranger_create = client.post(
        "/api/v1/sessions",
        json={
            "target_name": "Unauthorized Infiltration",
            "scope": "WORKSPACE",
            "workspace_id": str(ws.id),
        },
        headers=headers_stranger,
    )
    assert stranger_create.status_code == 403

    # Unauthenticated caller cannot create session in Alice's workspace -> 403
    unauth_ws_create = client.post(
        "/api/v1/sessions",
        json={
            "target_name": "Unauth Workspace Infiltration",
            "scope": "WORKSPACE",
            "workspace_id": str(ws.id),
        },
    )
    assert unauth_ws_create.status_code == 403


def test_missing_or_invalid_authentication_token(client: TestClient):
    """Verify endpoints requiring authentication reject missing or corrupt tokens."""
    # 1. /auth/me with missing token -> 401
    resp_no_token = client.get("/api/v1/auth/me")
    assert resp_no_token.status_code == 401
    assert resp_no_token.json()["error"]["code"] == "NOT_AUTHENTICATED"

    # 2. /auth/me with invalid signature -> 401
    resp_bad_token = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer bad.token.value"})
    assert resp_bad_token.status_code == 401
    assert resp_bad_token.json()["error"]["code"] == "INVALID_TOKEN"

    # 3. Protected /research endpoints require authentication
    resp_research = client.get("/api/v1/research")
    assert resp_research.status_code == 401


def test_list_sessions_tenant_isolation(client: TestClient, db_session: Session):
    """Verify list endpoint isolates private sessions between users and hides them from unauthenticated users."""
    alice = create_user(db_session, "alice_isolation@changeradar.ai")
    bob = create_user(db_session, "bob_isolation@changeradar.ai")

    headers_alice = get_headers(client, "alice_isolation@changeradar.ai")
    headers_bob = get_headers(client, "bob_isolation@changeradar.ai")

    # Alice creates a private session
    resp = client.post(
        "/api/v1/sessions",
        json={
            "target_name": "Alice Secret Venture",
            "target_type": "company",
            "meeting_context": "Private M&A",
            "scope": "PERSONAL",
        },
        headers=headers_alice,
    )
    assert resp.status_code == 201
    alice_sess_id = resp.json()["id"]

    # Alice lists sessions -> must contain Alice's session
    alice_list = client.get("/api/v1/sessions", headers=headers_alice)
    assert alice_list.status_code == 200
    alice_session_ids = [s["id"] for s in alice_list.json()]
    assert alice_sess_id in alice_session_ids

    # Bob lists sessions -> must NOT contain Alice's session
    bob_list = client.get("/api/v1/sessions", headers=headers_bob)
    assert bob_list.status_code == 200
    bob_session_ids = [s["id"] for s in bob_list.json()]
    assert alice_sess_id not in bob_session_ids

    # Bob filters scope=PERSONAL -> must NOT contain Alice's session
    bob_personal = client.get("/api/v1/sessions?scope=PERSONAL", headers=headers_bob)
    assert bob_personal.status_code == 200
    bob_p_ids = [s["id"] for s in bob_personal.json()]
    assert alice_sess_id not in bob_p_ids

    # Unauthenticated caller lists sessions -> must NOT contain Alice's session
    unauth_list = client.get("/api/v1/sessions")
    assert unauth_list.status_code == 200
    unauth_session_ids = [s["id"] for s in unauth_list.json()]
    assert alice_sess_id not in unauth_session_ids


def test_demo_mode_does_not_permit_auth_bypass_to_private_research(client: TestClient, db_session: Session):
    """Verify unauthenticated callers cannot access private user research via demo bypass."""
    alice = create_user(db_session, "alice_demo_check@changeradar.ai")
    headers_alice = get_headers(client, "alice_demo_check@changeradar.ai")

    resp = client.post(
        "/api/v1/sessions",
        json={
            "target_name": "Strictly Confidential Target",
            "target_type": "company",
            "meeting_context": "NDA Protected",
            "scope": "PERSONAL",
        },
        headers=headers_alice,
    )
    assert resp.status_code == 201
    sess_id = resp.json()["id"]
    job_id = resp.json()["latest_job"]["id"]

    # Unauthenticated caller attempts access without auth token -> 404 Not Found
    assert client.get(f"/api/v1/sessions/{sess_id}").status_code == 404
    assert client.get(f"/api/v1/sessions/{sess_id}/briefing").status_code == 404
    assert client.get(f"/api/v1/sessions/{sess_id}/delta").status_code == 404
    assert client.post(f"/api/v1/sessions/{sess_id}/review", json={}).status_code == 404
    assert client.post(f"/api/v1/sessions/{sess_id}/stress-tests", json={"talking_points": ["test"]}).status_code == 404
    assert client.get(f"/api/v1/runs/{job_id}").status_code == 404
    # /jobs/{id} requires authenticated user token (401 when missing token)
    assert client.get(f"/api/v1/jobs/{job_id}").status_code in [401, 404]
    assert client.delete(f"/api/v1/sessions/{sess_id}").status_code == 404


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
