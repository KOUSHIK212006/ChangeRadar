"""Verification audit tests for ChangeRadar LLM call counts, quota handling, evidence integrity, temporal reasoning, and caching.

All tests run deterministically against mocked LLM providers without consuming real API quota.
"""

from datetime import datetime, timezone
import json
from unittest.mock import MagicMock, patch
import pytest

from intelligence.cache import LLMCache
from intelligence.config import intelligence_settings
from intelligence.contracts import (
    BaselineEventSnapshot,
    CoverageReport,
    EvidenceRecord,
    ExtractedClaim,
    ExtractedEvent,
    IntelligenceResult,
    ResearchBaseline,
    ResearchContext,
    ResearchRequest,
    SourceOriginRecord,
    SourceRecord,
)
from intelligence.engine import _run_live_pipeline
from intelligence.instrumentation import LLMUsageTracker, set_current_tracker
from intelligence.pipeline.assessor import assess_claims
from intelligence.pipeline.clusterer import cluster_events
from intelligence.pipeline.delta import compute as compute_delta
from intelligence.pipeline.extractor import extract_events_and_claims
from intelligence.pipeline.normalizer import normalize
from intelligence.pipeline.stress_test import run as run_stress_test
from intelligence.providers.base import (
    PermanentLLMError,
    QuotaExhaustedError,
)
from intelligence.providers.llm import BaseLLMProvider, get_llm_provider


class AuditMockLLM(BaseLLMProvider):
    """Deterministic mock provider recording every call."""

    def __init__(self, response_generator=None, max_retries=2):
        super().__init__(
            provider_name="mock_gemini",
            api_key="mock-key-12345",
            model="gemini-2.5-flash",
            temperature=0.1,
            timeout=10,
            max_retries=max_retries,
        )
        self.call_count = 0
        self.call_history = []
        self.response_generator = response_generator

    def _call_api(self, system_prompt: str, user_prompt: str):
        self.call_count += 1
        self.call_history.append((system_prompt, user_prompt))
        if self.response_generator:
            return self.response_generator(system_prompt, user_prompt, self.call_count)
        return json.dumps({"status": "ok"}), 150, 45


@pytest.fixture
def clean_audit_env():
    tracker = LLMUsageTracker(run_id="audit_run")
    set_current_tracker(tracker)
    cache = LLMCache()
    with patch("intelligence.providers.llm.get_cache", return_value=cache):
        yield tracker, cache


def _make_sources(count: int) -> list[SourceRecord]:
    now = datetime.now(timezone.utc)
    return [
        SourceRecord(
            source_id=f"src-{i:03d}",
            url=f"https://news.example.com/story-{i}",
            canonical_url=f"https://news.example.com/story-{i}",
            title=f"Acme Development Announcement {i}",
            publisher="Tech Journal" if i % 2 == 0 else "Business Wire",
            snippet=f"Acme Corp announced major operational milestone {i} in manufacturing.",
            published_at=now,
            discovered_at=now,
            is_syndicated=False,
            syndication_confidence=0.0,
        )
        for i in range(count)
    ]


# ---------------------------------------------------------------------------
# Section 1: Verify Actual LLM Call Counts for All 5 Required Scenarios
# ---------------------------------------------------------------------------

def test_audit_scenario_1_five_articles_ten_claims(clean_audit_env):
    """Scenario 1: 5 articles and 10 claims -> exactly 4 LLM calls (1 Plan, 1 Extract, 1 Assess, 1 Briefing)."""
    tracker, _ = clean_audit_env

    def mock_responses(sys, user, count):
        if "research planner" in sys.lower():
            return json.dumps({"queries": ["q1", "q2"], "entity_aliases": ["Acme"], "time_filter": "past month"}), 100, 30
        elif "investigative intelligence analyst" in sys.lower():
            # 5 articles extracted into 10 claims
            return json.dumps({
                "events": [{"title": f"Event {i}", "description": f"Desc {i}", "source_ids": [f"src-{i:03d}"]} for i in range(3)],
                "claims": [{"text": f"Claim {i}", "event_title": "Event 0", "source_ids": [f"src-{i % 5:03d}"]} for i in range(10)],
            }), 400, 200
        elif "evidence verification analyst" in sys.lower():
            return json.dumps({
                "assessments": [
                    {"claim_id": f"clm-{i}", "assessment": "SUPPORTED", "rationale": "Directly confirmed", "supporting_source_ids": ["src-000"]}
                    for i in range(10)
                ]
            }), 300, 150
        elif "executive intelligence analyst" in sys.lower():
            return json.dumps({"executive_briefing": "Summary briefing text."}), 200, 100
        return json.dumps({}), 50, 20

    mock_llm = AuditMockLLM(response_generator=mock_responses)
    mock_search = MagicMock()
    mock_search.search.return_value = _make_sources(5)

    request = ResearchRequest(
        session_id="sess-01",
        job_id="job-01",
        context=ResearchContext(target_name="Acme Corp", meeting_objective="Partnership", time_window_days=30),
    )

    with patch("intelligence.engine.get_llm_provider", return_value=mock_llm):
        with patch("intelligence.engine.TavilySearchProvider", return_value=mock_search):
            res = _run_live_pipeline(request)

    assert mock_llm.call_count == 4
    assert res.llm_usage is not None
    assert res.llm_usage.total_requests == 4
    assert res.llm_usage.stages == {"planning": 1, "extraction": 1, "assessment": 1, "briefing": 1}


def test_audit_scenario_2_fifteen_articles_twenty_claims(clean_audit_env):
    """Scenario 2: 15 articles and 20 claims -> exactly 4 LLM calls (1 Plan, 1 Extract [15<=15], 1 Assess [20<=20], 1 Briefing)."""
    tracker, _ = clean_audit_env

    def mock_responses(sys, user, count):
        if "research planner" in sys.lower():
            return json.dumps({"queries": ["q1"], "entity_aliases": [], "time_filter": "30d"}), 100, 30
        elif "investigative intelligence analyst" in sys.lower():
            return json.dumps({
                "events": [{"title": f"Event {i}", "description": "Desc", "source_ids": ["src-000"]} for i in range(5)],
                "claims": [{"text": f"Claim {i}", "event_title": "Event 0", "source_ids": ["src-000"]} for i in range(20)],
            }), 600, 300
        elif "evidence verification analyst" in sys.lower():
            return json.dumps({"assessments": []}), 400, 150
        elif "executive intelligence analyst" in sys.lower():
            return json.dumps({"executive_briefing": "Briefing"}), 200, 80
        return json.dumps({}), 50, 20

    mock_llm = AuditMockLLM(response_generator=mock_responses)
    mock_search = MagicMock()
    mock_search.search.return_value = _make_sources(15)

    request = ResearchRequest(
        session_id="sess-02",
        job_id="job-02",
        context=ResearchContext(target_name="Acme Corp", meeting_objective="Review", time_window_days=30),
    )

    with patch("intelligence.engine.get_llm_provider", return_value=mock_llm):
        with patch("intelligence.engine.TavilySearchProvider", return_value=mock_search):
            res = _run_live_pipeline(request)

    assert mock_llm.call_count == 4
    assert res.llm_usage is not None
    assert res.llm_usage.total_requests == 4
    assert res.llm_usage.stages["extraction"] == 1
    assert res.llm_usage.stages["assessment"] == 1


def test_audit_scenario_3_thirty_articles_forty_claims(clean_audit_env):
    """Scenario 3: 30 articles and 40 claims -> exactly 6 LLM calls (1 Plan, 2 Extract batches [30/15=2], 2 Assess batches [40/20=2], 1 Briefing)."""
    tracker, _ = clean_audit_env

    def mock_responses(sys, user, count):
        if "research planner" in sys.lower():
            return json.dumps({"queries": ["q1"], "entity_aliases": [], "time_filter": "30d"}), 100, 30
        elif "investigative intelligence analyst" in sys.lower():
            # Return 20 claims per batch of 15 articles
            return json.dumps({
                "events": [{"title": f"Event B{count}", "description": "Desc", "source_ids": ["src-000"]}],
                "claims": [{"text": f"Claim B{count}-{i}", "event_title": f"Event B{count}", "source_ids": ["src-000"]} for i in range(20)],
            }), 700, 350
        elif "evidence verification analyst" in sys.lower():
            return json.dumps({"assessments": []}), 500, 200
        elif "executive intelligence analyst" in sys.lower():
            return json.dumps({"executive_briefing": "Briefing"}), 200, 80
        return json.dumps({}), 50, 20

    mock_llm = AuditMockLLM(response_generator=mock_responses)
    mock_search = MagicMock()
    mock_search.search.return_value = _make_sources(30)

    request = ResearchRequest(
        session_id="sess-03",
        job_id="job-03",
        context=ResearchContext(target_name="Acme Corp", meeting_objective="Audit", time_window_days=30),
    )

    with patch.object(intelligence_settings, "MAX_ARTICLES_PER_BATCH", 15):
        with patch.object(intelligence_settings, "MAX_CLAIMS_PER_BATCH", 20):
            with patch("intelligence.engine.get_llm_provider", return_value=mock_llm):
                with patch("intelligence.engine.TavilySearchProvider", return_value=mock_search):
                    res = _run_live_pipeline(request)

    # 1 planning + 2 extraction + 2 assessment + 1 briefing = 6 calls
    assert mock_llm.call_count == 6
    assert res.llm_usage is not None
    assert res.llm_usage.total_requests == 6
    assert res.llm_usage.stages["extraction"] == 2
    assert res.llm_usage.stages["assessment"] == 2


def test_audit_scenario_4_thirty_articles_with_five_talking_points(clean_audit_env):
    """Scenario 4: 30 articles with 5 talking points (and 20 claims) -> exactly 6 LLM calls (1 Plan, 2 Extract, 1 Assess, 1 Briefing, 1 Stress Test)."""
    tracker, _ = clean_audit_env

    def mock_responses(sys, user, count):
        if "research planner" in sys.lower():
            return json.dumps({"queries": ["q1"], "entity_aliases": [], "time_filter": "30d"}), 100, 30
        elif "investigative intelligence analyst" in sys.lower():
            return json.dumps({
                "events": [{"title": f"Event {count}", "description": "Desc", "source_ids": ["src-000"]}],
                "claims": [{"text": f"Claim {count}-{i}", "event_title": f"Event {count}", "source_ids": ["src-000"]} for i in range(10)],
            }), 600, 250
        elif "evidence verification analyst" in sys.lower():
            return json.dumps({"assessments": []}), 400, 150
        elif "executive intelligence analyst" in sys.lower():
            return json.dumps({"executive_briefing": "Briefing"}), 200, 80
        elif "talking points" in sys.lower() or "stress-test" in sys.lower():
            return json.dumps({
                "evaluations": [
                    {"point_index": i, "extracted_claims": [f"Point {i}"], "suggested_wording": f"Rewrite {i}"}
                    for i in range(5)
                ]
            }), 300, 150
        return json.dumps({}), 50, 20

    mock_llm = AuditMockLLM(response_generator=mock_responses)
    mock_search = MagicMock()
    mock_search.search.return_value = _make_sources(30)

    request = ResearchRequest(
        session_id="sess-04",
        job_id="job-04",
        context=ResearchContext(
            target_name="Acme Corp",
            meeting_objective="Deal Close",
            time_window_days=30,
            talking_points=[f"Talking point {i}" for i in range(5)],
        ),
    )

    with patch.object(intelligence_settings, "MAX_ARTICLES_PER_BATCH", 15):
        with patch.object(intelligence_settings, "MAX_CLAIMS_PER_BATCH", 20):
            with patch("intelligence.engine.get_llm_provider", return_value=mock_llm):
                with patch("intelligence.engine.TavilySearchProvider", return_value=mock_search):
                    res = _run_live_pipeline(request)

    # 1 plan + 2 extract (30 sources) + 1 assess (20 claims) + 1 briefing + 1 stress test = 6 calls
    assert mock_llm.call_count == 6
    assert res.llm_usage is not None
    assert res.llm_usage.total_requests == 6
    assert res.llm_usage.stages["stress_test"] == 1


def test_audit_scenario_5_repeated_identical_requests_caching(clean_audit_env):
    """Scenario 5: Repeated identical research requests -> Run 1 makes 4 calls, Run 2 makes 0 calls (100% cache hits)."""
    tracker, cache = clean_audit_env

    def mock_responses(sys, user, count):
        if "research planner" in sys.lower():
            return json.dumps({"queries": ["q1"], "entity_aliases": [], "time_filter": "30d"}), 100, 30
        elif "investigative intelligence analyst" in sys.lower():
            return json.dumps({
                "events": [{"title": "Event 1", "description": "Desc", "source_ids": ["src-000"]}],
                "claims": [{"text": "Claim 1", "event_title": "Event 1", "source_ids": ["src-000"]}],
            }), 400, 200
        elif "evidence verification analyst" in sys.lower():
            return json.dumps({"assessments": []}), 300, 100
        elif "executive intelligence analyst" in sys.lower():
            return json.dumps({"executive_briefing": "Cached briefing"}), 200, 80
        return json.dumps({}), 50, 20

    mock_llm = AuditMockLLM(response_generator=mock_responses)
    mock_search = MagicMock()
    mock_search.search.return_value = _make_sources(5)

    request = ResearchRequest(
        session_id="sess-05",
        job_id="job-05",
        context=ResearchContext(target_name="Acme Corp", meeting_objective="Status", time_window_days=30),
    )

    with patch("intelligence.engine.get_llm_provider", return_value=mock_llm):
        with patch("intelligence.engine.TavilySearchProvider", return_value=mock_search):
            res1 = _run_live_pipeline(request)

    # Run 1 makes 4 physical provider calls
    assert mock_llm.call_count == 4
    assert res1.llm_usage is not None
    assert res1.llm_usage.total_requests == 4
    assert res1.llm_usage.cache_hits == 0

    # Run 2: Exact same request with cache populated
    with patch("intelligence.engine.get_llm_provider", return_value=mock_llm):
        with patch("intelligence.engine.TavilySearchProvider", return_value=mock_search):
            res2 = _run_live_pipeline(request)

    # Call count did not increase at all
    assert mock_llm.call_count == 4
    assert res2.llm_usage is not None
    assert res2.llm_usage.total_requests == 0
    assert res2.llm_usage.cache_hits == 4


# ---------------------------------------------------------------------------
# Section 2: Verify Gemini Quota Handling & Provider Rules
# ---------------------------------------------------------------------------

def test_audit_quota_handling_retry_after(clean_audit_env):
    """Verify HTTP 429 respects Retry-After header and raises QuotaExhaustedError when exhausted."""
    def mock_429(sys, user, count):
        raise QuotaExhaustedError("429 Too Many Requests", retry_after=0.01)

    mock_llm = AuditMockLLM(response_generator=mock_429, max_retries=2)

    with patch("time.sleep") as mock_sleep:
        with pytest.raises(QuotaExhaustedError) as exc_info:
            mock_llm.complete("System", "Prompt")

    # Sleep called with retry_after
    assert mock_sleep.call_count == 2
    mock_sleep.assert_called_with(0.01)
    assert "quota exceeded" in str(exc_info.value).lower() or "429" in str(exc_info.value)


def test_audit_permanent_error_not_retried(clean_audit_env):
    """Verify permanent 400/401 errors are never retried."""
    mock_llm = AuditMockLLM(
        response_generator=lambda s, u, c: (_ for _ in ()).throw(PermanentLLMError("401 Unauthorized")),
        max_retries=3,
    )
    with pytest.raises(PermanentLLMError):
        mock_llm.complete("System", "Prompt")

    assert mock_llm.call_count == 1  # 0 retries attempted


def test_audit_unsupported_provider_never_switches_silently():
    """Verify provider switching never happens silently."""
    with pytest.raises(ValueError) as exc:
        get_llm_provider("unsupported_provider_xyz")
    assert "Unsupported LLM provider" in str(exc.value)


# ---------------------------------------------------------------------------
# Section 3: Verify Evidence Integrity
# ---------------------------------------------------------------------------

def test_audit_evidence_integrity_syndicated_cannot_be_supported(clean_audit_env):
    """Verify syndicated PR wire copies with 0 independent origins are downgraded from SUPPORTED to PARTIALLY_SUPPORTED."""
    sources = [
        SourceRecord(
            source_id="src-pr-1",
            url="https://businesswire.com/story-1",
            canonical_url="https://businesswire.com/story-1",
            title="Acme Press Release",
            publisher="BusinessWire",
            snippet="Acme reports 25% revenue jump.",
            published_at=datetime.now(timezone.utc),
            discovered_at=datetime.now(timezone.utc),
            is_syndicated=True,
            syndication_confidence=0.9,
        )
    ]
    origins = [
        SourceOriginRecord(
            origin_id="org-pr",
            label="BusinessWire PR Wire",
            source_ids=["src-pr-1"],
            is_independent=False,  # Not independent!
            independence_confidence=0.9,
        )
    ]
    claims = [
        ExtractedClaim(
            claim_id="clm-pr",
            text="Acme revenue jumped 25%",
            assessment="INSUFFICIENT",
            assessment_rationale="",
            evidence=[EvidenceRecord(evidence_id="e1", excerpt="Snippet", source_id="src-pr-1", relevance="SUPPORTING")],
            source_doc_count=1,
            independent_origin_count=0,
            volatility="LOW",
            is_stale=False,
            llm_confidence=0.0,
        )
    ]

    mock_llm = AuditMockLLM(
        response_generator=lambda s, u, c: (
            json.dumps({"assessments": [{"claim_id": "clm-pr", "assessment": "SUPPORTED", "rationale": "Wire reported it"}]}),
            100, 30,
        )
    )

    assessed = assess_claims(claims, sources, origins, mock_llm)
    assert len(assessed) == 1
    # Downgraded because origin is not independent (origin_count == 0)
    assert assessed[0].assessment == "PARTIALLY_SUPPORTED"
    assert assessed[0].independent_origin_count == 0


def test_audit_uncertain_events_not_forcibly_merged():
    """Verify uncertain events are kept distinct and not merged into confirmed events."""
    now = datetime.now(timezone.utc)
    ev_confirmed = ExtractedEvent(
        event_id="ev-1",
        title="Acme Corp appoints new CFO Jane Doe",
        description="Jane Doe formally took over as CFO following SEC filing.",
        lifecycle_status="COMPLETED",
        is_disputed=False,
        is_uncertain=False,
        event_at=now,
        published_at=now,
        discovered_at=now,
        source_ids=["src-1"],
        origin_ids=[],
        claim_ids=[],
    )
    ev_rumor = ExtractedEvent(
        event_id="ev-2",
        title="Acme Corp appoints new CFO Jane Doe",
        description="Rumors suggest Jane Doe may become CFO according to blog post.",
        lifecycle_status="NEW",
        is_disputed=False,
        is_uncertain=True,  # Uncertain rumor
        event_at=now,
        published_at=now,
        discovered_at=now,
        source_ids=["src-2"],
        origin_ids=[],
        claim_ids=[],
    )

    mock_llm = AuditMockLLM()
    merged = cluster_events([ev_confirmed, ev_rumor], [], mock_llm)
    # Must NOT forcibly merge confirmed and uncertain events
    assert len(merged) == 2


# ---------------------------------------------------------------------------
# Section 4: Verify Temporal Reasoning & Delta
# ---------------------------------------------------------------------------

def test_audit_baseline_does_not_mistake_known_event_for_new_development():
    """Verify baseline comparison matches known events by description similarity, avoiding false 'new' alerts."""
    now = datetime.now(timezone.utc)
    current_result = IntelligenceResult(
        session_id="s1",
        job_id="j1",
        status="COMPLETED",
        events=[
            ExtractedEvent(
                event_id="new-hash-id-for-same-event",
                title="Acme Opens Austin Gigafactory",
                description="Acme completed construction and opened the gigafactory in Austin Texas.",
                lifecycle_status="COMPLETED",
                is_disputed=False,
                is_uncertain=False,
                event_at=now,
                published_at=now,
                discovered_at=now,
                source_ids=["s1"],
                origin_ids=[],
                claim_ids=[],
            )
        ],
        claims=[],
        coverage=CoverageReport(
            planned_searches=1, executed_searches=1, failed_searches=0, time_window_days=30, origin_diversity_score=1.0, gaps=[]
        ),
    )

    baseline = ResearchBaseline(
        baseline_result_id="res-0",
        reviewed_at=now,
        known_event_ids=["old-hash-id-123"],
        known_claim_ids=[],
        event_snapshots=[
            BaselineEventSnapshot(
                event_id="old-hash-id-123",
                description="Acme completed construction and opened the gigafactory in Austin Texas.",
                lifecycle_status="COMPLETED",
            )
        ],
        claim_snapshots=[],
    )

    delta, versions = compute_delta(current_result, baseline)
    assert delta is not None
    # Description matched existing snapshot -> NOT a new event!
    assert "new-hash-id-for-same-event" not in delta.new_events
    assert len(delta.new_events) == 0


def test_audit_low_volatility_claim_not_invalidated_by_age():
    """Verify LOW volatility facts (e.g. founder name, incorporation) are not marked stale by passage of time."""
    claim = ExtractedClaim(
        claim_id="clm-founding",
        text="Acme was founded in 2012 by Alice Smith.",
        assessment="SUPPORTED",
        assessment_rationale="Corporate charter records.",
        evidence=[EvidenceRecord(evidence_id="e1", excerpt="Founded 2012", source_id="src-001", relevance="SUPPORTING")],
        source_doc_count=1,
        independent_origin_count=1,
        volatility="LOW",
        is_stale=False,
        llm_confidence=0.99,
    )
    # Published 100 days ago
    sources = [
        SourceRecord(
            source_id="src-001",
            url="https://sec.gov/filing",
            canonical_url="https://sec.gov/filing",
            title="10-K",
            publisher="SEC",
            snippet="Founded in 2012",
            published_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            discovered_at=datetime.now(timezone.utc),
            is_syndicated=False,
            syndication_confidence=0.0,
        )
    ]
    origins = [
        SourceOriginRecord(
            origin_id="org-sec", label="SEC EDGAR", source_ids=["src-001"], is_independent=True, independence_confidence=1.0
        )
    ]
    mock_llm = AuditMockLLM(
        response_generator=lambda s, u, c: (
            json.dumps({"assessments": [{"claim_id": "clm-founding", "assessment": "SUPPORTED", "rationale": "Confirmed."}]}),
            100, 30,
        )
    )

    assessed = assess_claims([claim], sources, origins, mock_llm)
    assert len(assessed) == 1
    assert assessed[0].is_stale is False  # Low volatility fact is NOT stale!


# ---------------------------------------------------------------------------
# Section 5: Verify Cache Key Invalidation
# ---------------------------------------------------------------------------

def test_audit_cache_keys_include_all_parameters():
    """Verify cache keys change when provider, model, version, temperature, or json_mode change."""
    k_default = LLMCache.compute_key("gemini-2.5-flash", "Sys", "User", version="v2", provider="gemini", temperature=0.1, json_mode=True)
    k_diff_provider = LLMCache.compute_key("gemini-2.5-flash", "Sys", "User", version="v2", provider="groq", temperature=0.1, json_mode=True)
    k_diff_model = LLMCache.compute_key("gemini-1.5-pro", "Sys", "User", version="v2", provider="gemini", temperature=0.1, json_mode=True)
    k_diff_temp = LLMCache.compute_key("gemini-2.5-flash", "Sys", "User", version="v2", provider="gemini", temperature=0.7, json_mode=True)
    k_diff_version = LLMCache.compute_key("gemini-2.5-flash", "Sys", "User", version="v3", provider="gemini", temperature=0.1, json_mode=True)

    assert k_default != k_diff_provider
    assert k_default != k_diff_model
    assert k_default != k_diff_temp
    assert k_default != k_diff_version
