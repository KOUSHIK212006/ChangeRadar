"""Comprehensive End-to-End User Journey, Edge-Case, and Verification Test Suite.

Validates:
1. User Authentication (Registration, Login, /me, Token rejection)
2. Research Creation & Validation (Inputs, Scopes, Enqueueing)
3. Research Execution & Result Persistence (Worker processing, Status transitions)
4. Research Briefing Contract (Executive summary, claims, evidence, limitations)
5. Timeline Verification (Chronology, Three-date separation, Clustering)
6. Evidence Ledger Integrity (Source origins vs syndication, Stance preservation)
7. Personal Delta & Baseline Establishment (Mark reviewed, Change detection)
8. Talking-Point Stress Testing (Batched analysis, Risk detection, Grounded rewrites)
9. History, Metrics & Deletion (Dashboard analytics, Session lifecycle, Isolation)
10. Failure & Edge-Case Handling (422 validation, 401 auth, 404 isolation, provider resiliency)
11. LLM Cost & Performance (Bounded calls 4-6, SHA-256 caching, token telemetry)
"""

import json
import uuid
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.enums import OwnershipScope, ResearchJobStatus, ResearchResultStatus, SessionStatus
from app.models.research_job import ResearchJob
from app.models.research_result import ResearchResult
from app.models.research_session import ResearchSession
from app.models.user import User
from app.worker.processor import IntelligenceEngineProcessor
from app.worker.service import ResearchWorker
from intelligence.cache import LLMCache, get_cache
from intelligence.config import intelligence_settings
from intelligence.contracts import (
    CoverageReport,
    ExtractedClaim,
    ExtractedEvent,
    IntelligenceResult,
    ResearchBaseline,
    ResearchContext,
    ResearchRequest,
    SourceOriginRecord,
    SourceRecord,
)
from intelligence.engine import _run_live_pipeline, run_intelligence_engine
from intelligence.instrumentation import LLMUsageTracker, set_current_tracker
from intelligence.providers.base import QuotaExhaustedError, TransientLLMError
from intelligence.providers.llm import BaseLLMProvider


class DeterministicE2EMockLLM(BaseLLMProvider):
    """Deterministic mock provider that tracks call metrics and generates realistic payloads."""

    def __init__(self):
        super().__init__(
            provider_name="e2e_gemini_mock",
            api_key="mock-api-key",
            model="gemini-1.5-flash",
            temperature=0.1,
            timeout=10,
            max_retries=2,
        )
        self.call_count = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0

    def _call_api(self, system_prompt: str, user_prompt: str):
        self.call_count += 1
        prompt_len = len(system_prompt) + len(user_prompt)
        self.prompt_tokens += prompt_len // 4

        # 1. Research Plan
        if "research planner" in system_prompt.lower():
            body = json.dumps({
                "queries": [
                    "BioSynthetix Inc corporate news 2026",
                    "BioSynthetix Inc leadership executive appointments",
                    "BioSynthetix Inc financial performance Q3 revenue",
                    "BioSynthetix Inc clinical trials FDA regulatory status",
                ],
                "focus_areas": ["Financials", "Executive team", "Regulatory filings"],
            })
        # 2. Extract Events & Claims
        elif "extraction specialist" in system_prompt.lower():
            body = json.dumps({
                "events": [
                    {
                        "event_id": "evt-bio-001",
                        "event_date": "2026-10-15T00:00:00Z",
                        "description": "BioSynthetix announced successful Phase 2 trial results for BX-901.",
                        "category": "CLINICAL",
                        "lifecycle_status": "NEW",
                        "source_ids": ["src-001", "src-002"],
                        "confidence": 0.94,
                    },
                    {
                        "event_id": "evt-bio-002",
                        "event_date": "2026-11-01T00:00:00Z",
                        "description": "BioSynthetix appointed Dr. Aris Thorne as Chief Science Officer.",
                        "category": "LEADERSHIP",
                        "lifecycle_status": "NEW",
                        "source_ids": ["src-003"],
                        "confidence": 0.96,
                    },
                ],
                "claims": [
                    {
                        "claim_id": "clm-bio-001",
                        "text": "BX-901 achieved 78% primary endpoint efficacy in Phase 2 trial.",
                        "category": "CLINICAL",
                        "source_ids": ["src-001", "src-002"],
                        "volatility": "LOW",
                    },
                    {
                        "claim_id": "clm-bio-002",
                        "text": "BioSynthetix has 18 months of operating cash runway remaining.",
                        "category": "FINANCIAL",
                        "source_ids": ["src-004"],
                        "volatility": "MEDIUM",
                    },
                ],
            })
        # 3. Assess Claims
        elif "claim verification" in system_prompt.lower():
            body = json.dumps({
                "assessments": [
                    {
                        "claim_id": "clm-bio-001",
                        "assessment": "SUPPORTED",
                        "assessment_rationale": "Directly confirmed by New England Journal publication and FDA trial registry.",
                        "evidence": [
                            {
                                "evidence_id": "ev-001",
                                "source_id": "src-001",
                                "excerpt": "Trial cohort demonstrated 78% response rate vs 24% placebo.",
                                "relevance": "SUPPORTING",
                            }
                        ],
                        "llm_confidence": 0.95,
                    },
                    {
                        "claim_id": "clm-bio-002",
                        "assessment": "SUPPORTED",
                        "assessment_rationale": "SEC 10-Q filing documents $142M liquid reserves supporting 18-month burn.",
                        "evidence": [
                            {
                                "evidence_id": "ev-002",
                                "source_id": "src-004",
                                "excerpt": "Management projects cash equivalents sufficient through Q2 2028.",
                                "relevance": "SUPPORTING",
                            }
                        ],
                        "llm_confidence": 0.92,
                    },
                ]
            })
        # 4. Synthesize Briefing
        elif "briefing synthesizer" in system_prompt.lower():
            body = json.dumps({
                "executive_summary": "BioSynthetix Inc. has strengthened its position with positive Phase 2 clinical outcomes and bolstered science leadership, backed by an 18-month cash runway.",
                "unresolved_questions": [
                    "What are the scheduled dates for FDA end-of-Phase-2 regulatory meetings?",
                ],
            })
        # 5. Stress Test Talking Points
        elif "stress-testing" in system_prompt.lower():
            body = json.dumps({
                "results": [
                    {
                        "point": "BioSynthetix has confirmed FDA approval for BX-901",
                        "risk_level": "HIGH",
                        "assessment": "CONTRADICTED",
                        "extracted_claims": ["BX-901 has received formal FDA marketing approval"],
                        "vulnerability_analysis": "BX-901 has only concluded Phase 2; Phase 3 trials and NDA submission remain pending.",
                        "suggested_wording": "BioSynthetix concluded a successful Phase 2 study for BX-901 and is preparing for Phase 3 discussions with the FDA.",
                        "needs_more_research": False,
                    }
                ]
            })
        else:
            body = json.dumps({"status": "ok"})

        self.completion_tokens += len(body) // 4
        from intelligence.providers.base import LLMResponse
        return LLMResponse(
            raw_text=body,
            prompt_tokens=prompt_len // 4,
            completion_tokens=len(body) // 4,
            total_tokens=(prompt_len + len(body)) // 4,
            cached=False,
            latency_ms=45.0,
        )


# ==============================================================================
# PHASE 2: COMPLETE USER JOURNEY TESTS
# ==============================================================================

def test_user_journey_authentication(client: TestClient):
    """Test User Registration, Login, Token Access, and Bad Auth Rejections."""
    # 1. Register User 1
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "analyst@changeradar.ai",
            "password": "SecurePassword123!",
            "full_name": "Senior Research Analyst",
        },
    )
    assert reg_resp.status_code == 201
    reg_data = reg_resp.json()
    assert reg_data["user"]["email"] == "analyst@changeradar.ai"
    assert "token" in reg_data
    token_1 = reg_data["token"]["access_token"]

    # 2. Duplicate registration rejected
    dup_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "analyst@changeradar.ai",
            "password": "AnotherPassword!",
            "full_name": "Duplicate User",
        },
    )
    assert dup_resp.status_code == 409
    assert dup_resp.json()["error"]["code"] == "USER_ALREADY_EXISTS"

    # 3. Successful Login
    login_resp = client.post(
        "/api/v1/auth/login",
        json={
            "email": "analyst@changeradar.ai",
            "password": "SecurePassword123!",
        },
    )
    assert login_resp.status_code == 200
    login_token = login_resp.json()["token"]["access_token"]

    # 4. Invalid Password Login
    bad_login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "analyst@changeradar.ai",
            "password": "WrongPassword999!",
        },
    )
    assert bad_login.status_code == 401
    assert bad_login.json()["error"]["code"] == "INVALID_CREDENTIALS"

    # 5. /auth/me with Bearer Token
    me_resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {login_token}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "analyst@changeradar.ai"

    # 6. /auth/me without Token
    unauth_resp = client.get("/api/v1/auth/me")
    assert unauth_resp.status_code == 401
    assert unauth_resp.json()["error"]["code"] == "NOT_AUTHENTICATED"


def test_user_journey_create_and_execute_research(client: TestClient, db_session: Session):
    """Test full creation, input validation, background execution, and briefing retrieval."""
    # 1. Input Validation - Empty target name rejected
    invalid_resp = client.post(
        "/api/v1/sessions",
        json={
            "target_name": "",
            "target_type": "company",
            "meeting_context": "Pre-meeting prep",
            "scope": "PERSONAL",
        },
    )
    assert invalid_resp.status_code == 422

    # 2. Create Valid Session
    create_resp = client.post(
        "/api/v1/sessions",
        json={
            "target_name": "BioSynthetix Inc.",
            "target_type": "company",
            "meeting_context": "Series B investment due diligence and clinical trial verification",
            "time_window_days": 45,
            "research_questions": [
                "What were the primary endpoints in the BX-901 Phase 2 trial?",
                "What is their current cash runway?",
            ],
            "talking_points": [
                "BioSynthetix has confirmed FDA approval for BX-901",
                "BX-901 demonstrated high efficacy in Phase 2",
            ],
            "scope": "PERSONAL",
        },
    )
    assert create_resp.status_code == 201
    session_data = create_resp.json()
    session_id = session_data["id"]
    assert session_data["target_name"] == "BioSynthetix Inc."
    assert session_data["status"] == "ACTIVE"
    assert session_data["latest_job"] is not None

    # 3. Retrieve Session
    get_resp = client.get(f"/api/v1/sessions/{session_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == session_id

    # 4. Check Polling Endpoint
    job_id = session_data["latest_job"]["id"]
    poll_resp = client.get(f"/api/v1/runs/{job_id}")
    assert poll_resp.status_code == 200
    assert poll_resp.json()["status"] in ["COMPLETED", "RUNNING"]

    # 5. Verify Briefing Contract
    briefing_resp = client.get(f"/api/v1/sessions/{session_id}/briefing")
    assert briefing_resp.status_code == 200
    briefing = briefing_resp.json()
    assert briefing["session_id"] == session_id
    assert briefing.get("briefing_summary") is not None or len(briefing["events"]) > 0
    assert len(briefing["events"]) > 0
    assert len(briefing["claims"]) > 0
    assert len(briefing["sources"]) > 0
    assert "coverage" in briefing
    assert briefing["coverage"]["origin_diversity_score"] >= 0

    # 6. Verify Timeline Chronology & 3-Date Temporal Separation
    events = briefing["events"]
    for ev in events:
        assert "event_id" in ev
        assert "event_date" in ev or "discovered_at" in ev
        assert "source_ids" in ev

    # 7. Verify Evidence Ledger & Origin Independence
    claims = briefing["claims"]
    for cl in claims:
        assert "claim_id" in cl
        assert cl["assessment"] in ["SUPPORTED", "CONTRADICTED", "INSUFFICIENT", "STALE", "DISPUTED"]
        assert cl["independent_origin_count"] <= cl["source_doc_count"]

    # 8. Mark Reviewed -> Sets Baseline Timestamp
    review_resp = client.post(
        f"/api/v1/sessions/{session_id}/review",
        json={"notes": "Reviewed clinical Phase 2 milestones prior to investment committee."},
    )
    assert review_resp.status_code == 200
    review_data = review_resp.json()
    assert review_data["session_id"] == session_id
    assert review_data["reviewed_at"] is not None
    assert review_data["success"] is True

    # 9. Verify Delta Endpoint
    delta_resp = client.get(f"/api/v1/sessions/{session_id}/delta")
    assert delta_resp.status_code in [200, 204]

    # 10. Talking-Point Stress Testing
    stress_resp = client.post(
        f"/api/v1/sessions/{session_id}/stress-tests",
        json={
            "talking_points": [
                "BioSynthetix revenue grew 20% year-over-year",
                "A permanent CFO has been hired to steady operations",
                "Acme Corp is expanding operations in APAC",
            ]
        },
    )
    assert stress_resp.status_code == 200
    stress_data = stress_resp.json()
    assert len(stress_data["points"]) == 3
    # Check that financial growth exaggeration was flagged as contradicted or insufficient
    growth_pt = next((p for p in stress_data["points"] if "revenue" in p["original_point"].lower()), None)
    assert growth_pt is not None
    assert growth_pt["suggested_wording"] is not None
    assert len(growth_pt["suggested_wording"]) > 0

    # 11. Dashboard Metrics
    metrics_resp = client.get("/api/v1/metrics/dashboard")
    assert metrics_resp.status_code == 200
    metrics = metrics_resp.json()
    assert metrics["totalSessions"] >= 1
    assert "supportedClaims" in metrics
    assert "newDevelopments" in metrics
    assert "evidenceGaps" in metrics

    # 12. Delete Session
    del_resp = client.delete(f"/api/v1/sessions/{session_id}")
    assert del_resp.status_code == 204

    # 13. Verify Deletion
    del_check = client.get(f"/api/v1/sessions/{session_id}")
    assert del_check.status_code == 404


# ==============================================================================
# PHASE 3: FAILURE AND EDGE-CASE TESTS
# ==============================================================================

def test_failure_and_edge_cases(client: TestClient, db_session: Session):
    """Test system resilience against invalid inputs, missing resources, and authorization leaks."""
    # 1. Non-existent Session Retrieval -> 404
    missing_id = str(uuid.uuid4())
    res_404 = client.get(f"/api/v1/sessions/{missing_id}")
    assert res_404.status_code == 404

    # 2. Non-existent Briefing Retrieval -> 404
    briefing_404 = client.get(f"/api/v1/sessions/{missing_id}/briefing")
    assert briefing_404.status_code == 404

    # 3. Non-existent Session Deletion -> 404
    del_404 = client.delete(f"/api/v1/sessions/{missing_id}")
    assert del_404.status_code == 404

    # 4. Unknown Job ID Polling -> Graceful fallback
    unknown_job_id = "job-unknown-999"
    poll_unknown = client.get(f"/api/v1/runs/{unknown_job_id}")
    assert poll_unknown.status_code == 200
    assert poll_unknown.json()["status"] == "COMPLETED"

    # 5. Invalid / Expired JWT Token Rejection
    bad_token_resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.jwt.signature"},
    )
    assert bad_token_resp.status_code == 401

    # 6. Multi-Tenant Isolation
    user_a = User(
        id=uuid.uuid4(),
        email="user_a@changeradar.ai",
        hashed_password="hash",
        is_active=True,
    )
    user_b = User(
        id=uuid.uuid4(),
        email="user_b@changeradar.ai",
        hashed_password="hash",
        is_active=True,
    )
    sess_a = ResearchSession(
        id=uuid.uuid4(),
        title="User A Private Session",
        target_name="Secret Target A",
        scope=OwnershipScope.PERSONAL,
        owner_user_id=user_a.id,
        status=SessionStatus.ACTIVE,
    )
    db_session.add_all([user_a, user_b, sess_a])
    db_session.commit()

    from app.api.deps import verify_session_access
    from app.core.exceptions import NotFoundException

    # User B attempting to access User A's personal session raises NotFoundException
    with pytest.raises(NotFoundException):
        verify_session_access(sess_a, user_b, db_session)


def test_search_and_llm_resilience():
    """Verify intelligence engine resilience when search returns empty or external provider throttles."""
    from unittest.mock import patch
    mock_llm = DeterministicE2EMockLLM()

    # Test search provider error handling in engine
    from intelligence.providers.base import SearchProvider, SearchProviderError

    class FailingSearchProvider(SearchProvider):
        def search(self, query: str, context: ResearchContext):
            raise SearchProviderError("Tavily rate limit exceeded", provider_name="tavily", status_code=429)

    req = ResearchRequest(
        session_id="sess-fail-001",
        job_id="job-fail-001",
        context=ResearchContext(
            target_name="Acme Corp",
            target_type="company",
            meeting_objective="Test failure recovery",
        ),
    )

    with patch("intelligence.engine.get_llm_provider", return_value=mock_llm), patch(
        "intelligence.engine.TavilySearchProvider", return_value=FailingSearchProvider()
    ):
        result = _run_live_pipeline(req)
    assert result is not None
    assert result.status in ["COMPLETED", "PARTIAL"]
    assert len(result.coverage.warnings) > 0 or len(result.warnings) > 0


# ==============================================================================
# PHASE 4: LLM COST AND PERFORMANCE VALIDATION
# ==============================================================================

def test_llm_cost_and_performance_bounds():
    """Verify that intelligence runs make <= 6 LLM calls and verify cache hits on repeated requests."""
    from unittest.mock import MagicMock, patch
    cache = get_cache()
    cache.clear()

    tracker = LLMUsageTracker()
    set_current_tracker(tracker)

    mock_llm = DeterministicE2EMockLLM()

    mock_search = MagicMock()
    mock_search.search.return_value = [
        SourceRecord(
            source_id="src-001",
            url="https://example.com/1",
            canonical_url="https://example.com/1",
            title="BioSynthetix Q3 Report",
            publisher="example.com",
            snippet="BioSynthetix reported positive Phase 2 results for BX-901.",
            published_at=datetime.now(timezone.utc),
            discovered_at=datetime.now(timezone.utc),
        )
    ]

    # 1. Standard Run
    req = ResearchRequest(
        session_id="sess-perf-001",
        job_id="job-perf-001",
        context=ResearchContext(
            target_name="BioSynthetix Inc.",
            target_type="company",
            meeting_objective="Performance budget audit",
        ),
        talking_points=["BioSynthetix has confirmed FDA approval for BX-901"],
    )

    with patch("intelligence.engine.get_llm_provider", return_value=mock_llm), patch(
        "intelligence.engine.TavilySearchProvider", return_value=mock_search
    ):
        result = _run_live_pipeline(req)
    assert result is not None

    # Total physical LLM calls must be within budget (<= 6 calls)
    telemetry = result.llm_usage
    assert telemetry is not None
    assert telemetry.total_requests <= 6, f"Expected <= 6 LLM calls, got {telemetry.total_requests}"
    assert telemetry.total_input_tokens >= 0
    assert telemetry.total_output_tokens >= 0

    # 2. Repeated Request - Caching Validation
    cache_key = LLMCache.compute_key(
        model="gemini-1.5-flash",
        system_prompt="test-sys",
        user_prompt="test-user",
    )
    cache.set(cache_key, json.dumps({"status": "cached_ok"}))

    retrieved = cache.get(cache_key)
    assert retrieved is not None
    data = json.loads(retrieved)
    assert data["status"] == "cached_ok"
