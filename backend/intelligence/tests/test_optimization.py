"""Verification tests for Gemini LLM optimization, batching, caching, quota handling, and telemetry.

All tests run deterministically against mocked LLM providers without consuming real API quota.
"""

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import pytest

from intelligence.cache import LLMCache
from intelligence.config import intelligence_settings
from intelligence.contracts import (
    CoverageReport,
    EvidenceRecord,
    ExtractedClaim,
    ExtractedEvent,
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
from intelligence.pipeline.planner import plan
from intelligence.pipeline.stress_test import run as run_stress_test
from intelligence.providers.base import (
    LLMParseError,
    PermanentLLMError,
    QuotaExhaustedError,
    TransientLLMError,
)
from intelligence.providers.llm import BaseLLMProvider


class MockLLM(BaseLLMProvider):
    """Deterministic mock provider with call counter and programmable responses."""

    def __init__(self, response_generator=None):
        super().__init__(
            provider_name="mock_gemini",
            api_key="mock-key-12345",
            model="gemini-1.5-flash",
            temperature=0.1,
            timeout=10,
            max_retries=2,
        )
        self.call_count = 0
        self.call_history = []
        self.response_generator = response_generator

    def _call_api(self, system_prompt: str, user_prompt: str):
        self.call_count += 1
        self.call_history.append((system_prompt, user_prompt))
        if self.response_generator:
            return self.response_generator(system_prompt, user_prompt, self.call_count)
        # Default mock response
        return json.dumps({"status": "ok"}), 150, 45


@pytest.fixture
def clean_tracker_and_cache():
    """Ensure clean telemetry tracker and cache for each test."""
    tracker = LLMUsageTracker(run_id="test_run")
    set_current_tracker(tracker)
    cache = LLMCache()
    with patch("intelligence.providers.llm.get_cache", return_value=cache):
        yield tracker, cache


def _create_sample_sources(count: int = 5) -> list[SourceRecord]:
    now = datetime.now(timezone.utc)
    return [
        SourceRecord(
            source_id=f"src-{i:03d}",
            url=f"https://news.example.com/story-{i}",
            canonical_url=f"https://news.example.com/story-{i}",
            title=f"Company Announcement Development {i}",
            publisher="Business Insider" if i % 2 == 0 else "BusinessWire",
            snippet=f"Acme Corp expanded operations and reported key metrics for division {i}.",
            published_at=now,
            discovered_at=now,
            is_syndicated=False,
            syndication_confidence=0.0,
        )
        for i in range(count)
    ]


# 1. Actual LLM request counting & telemetry
def test_llm_request_counting(clean_tracker_and_cache):
    tracker, _ = clean_tracker_and_cache
    mock_llm = MockLLM()

    mock_llm.complete("System prompt", "User prompt 1", stage="planning")
    mock_llm.complete("System prompt", "User prompt 2", stage="extraction")

    report = tracker.get_summary()
    assert report.total_requests == 2
    assert report.stages["planning"] == 1
    assert report.stages["extraction"] == 1
    assert report.cache_misses == 2
    assert report.cache_hits == 0


# 2. Multiple articles processed in batches
def test_multiple_articles_processed_in_batches(clean_tracker_and_cache):
    tracker, _ = clean_tracker_and_cache

    def mock_extract(sys, user, count):
        return json.dumps({
            "events": [{"title": f"Event from batch {count}", "description": "Desc", "source_ids": ["src-001"]}],
            "claims": [{"text": f"Claim from batch {count}", "source_ids": ["src-001"]}],
        }), 200, 80

    mock_llm = MockLLM(response_generator=mock_extract)
    sources = _create_sample_sources(25)  # 25 articles

    context = ResearchContext(
        target_name="Acme Corp",
        meeting_objective="Review expansion",
        time_window_days=30,
    )

    with patch.object(intelligence_settings, "MAX_ARTICLES_PER_BATCH", 15):
        events, claims = extract_events_and_claims(sources, context, mock_llm)

    # 25 articles with batch size 15 -> exactly 2 LLM requests!
    assert mock_llm.call_count == 2
    assert len(events) == 2
    assert len(claims) == 2


# 3. Multiple claims assessed in batches
def test_multiple_claims_assessed_in_batches(clean_tracker_and_cache):
    tracker, _ = clean_tracker_and_cache

    def mock_assess(sys, user, count):
        return json.dumps({
            "assessments": [
                {
                    "claim_id": f"clm-{i:03d}",
                    "assessment": "SUPPORTED",
                    "rationale": "Verified by sources.",
                    "supporting_source_ids": ["src-001"],
                }
                for i in range(20)
            ]
        }), 300, 150

    mock_llm = MockLLM(response_generator=mock_assess)
    sources = _create_sample_sources(3)
    origins = [
        SourceOriginRecord(
            origin_id="org-1", label="Reuters", source_ids=["src-000", "src-001"], is_independent=True, independence_confidence=0.9
        )
    ]

    claims = [
        ExtractedClaim(
            claim_id=f"clm-{i:03d}",
            text=f"Atomic factual statement number {i}",
            assessment="INSUFFICIENT",
            assessment_rationale="",
            evidence=[EvidenceRecord(evidence_id="e1", excerpt="Excerpt", source_id="src-001", relevance="SUPPORTING")],
            source_doc_count=1,
            independent_origin_count=1,
            volatility="LOW",
            is_stale=False,
            llm_confidence=0.0,
        )
        for i in range(25)
    ]

    with patch.object(intelligence_settings, "MAX_CLAIMS_PER_BATCH", 20):
        assessed = assess_claims(claims, sources, origins, mock_llm)

    # 25 claims with batch size 20 -> exactly 2 LLM calls!
    assert mock_llm.call_count == 2
    assert len(assessed) == 25


# 4. Cache hits preventing duplicate LLM requests
def test_cache_hits_prevent_duplicate_llm_requests(clean_tracker_and_cache):
    tracker, cache = clean_tracker_and_cache
    mock_llm = MockLLM()

    # Call 1: Miss
    r1 = mock_llm.complete("System prompt", "Identical query", stage="planning")
    assert mock_llm.call_count == 1

    # Call 2: Identical prompt should hit cache without calling API
    r2 = mock_llm.complete("System prompt", "Identical query", stage="planning")
    assert mock_llm.call_count == 1  # No additional physical call!
    assert r1 == r2

    summary = tracker.get_summary()
    assert summary.total_requests == 1
    assert summary.cache_hits == 1
    assert summary.cache_misses == 1


# 5. Cache invalidation when content or model changes
def test_cache_invalidation_when_content_changes(clean_tracker_and_cache):
    mock_llm = MockLLM()

    mock_llm.complete("System prompt", "Query version 1", stage="planning")
    mock_llm.complete("System prompt", "Query version 2 (changed content)", stage="planning")

    assert mock_llm.call_count == 2


# 6. Retry behavior on transient errors
def test_retry_behavior_on_transient_error(clean_tracker_and_cache):
    tracker, _ = clean_tracker_and_cache
    attempts = 0

    def mock_transient(sys, user, count):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise TransientLLMError("Simulated 503 Server Unavailable")
        return json.dumps({"status": "recovered"}), 100, 30

    mock_llm = MockLLM(response_generator=mock_transient)
    with patch("time.sleep"):  # skip actual sleep
        res = mock_llm.complete("System", "Prompt", stage="planning")

    assert json.loads(res)["status"] == "recovered"
    assert attempts == 2  # 1 initial + 1 retry

    summary = tracker.get_summary()
    assert summary.retries == 1
    assert summary.total_requests == 2


# 7. HTTP 429 quota exhaustion handling
def test_http_429_quota_exhaustion_detection(clean_tracker_and_cache):
    def mock_429(sys, user, count):
        raise QuotaExhaustedError("HTTP 429 Resource Exhausted")

    mock_llm = MockLLM(response_generator=mock_429)

    with patch("time.sleep"):
        with pytest.raises(QuotaExhaustedError) as exc_info:
            mock_llm.complete("System", "Prompt", stage="extraction")

    assert "quota exceeded" in str(exc_info.value).lower() or "429" in str(exc_info.value)


# 8. Partial batch failure recovery
def test_partial_batch_failures(clean_tracker_and_cache):
    def mock_partial_fail(sys, user, count):
        if "src-000" in user:
            # Batch 1 permanently fails
            raise PermanentLLMError("Batch 1 permanently invalid")
        return json.dumps({
            "events": [{"title": "Recovered Event", "description": "Good batch", "source_ids": ["src-010"]}],
            "claims": [],
        }), 120, 40

    mock_llm = MockLLM(response_generator=mock_partial_fail)
    sources = _create_sample_sources(20)
    context = ResearchContext(target_name="Acme Corp", meeting_objective="Status", time_window_days=30)

    with patch.object(intelligence_settings, "MAX_ARTICLES_PER_BATCH", 10):
        events, claims = extract_events_and_claims(sources, context, mock_llm)

    # Batch 1 failed permanently, Batch 2 succeeded -> 1 event recovered without crashing
    assert len(events) == 1
    assert events[0].title == "Recovered Event"


# 9. Malformed LLM responses
def test_malformed_llm_responses_handled_gracefully(clean_tracker_and_cache):
    def mock_invalid_json(sys, user, count):
        return "Not a valid JSON response", 50, 10

    mock_llm = MockLLM(response_generator=mock_invalid_json)
    with pytest.raises(LLMParseError):
        mock_llm.complete("System", "Prompt")


# 10. Source ID and evidence provenance preservation
def test_source_id_and_provenance_preservation(clean_tracker_and_cache):
    def mock_extract(sys, user, count):
        return json.dumps({
            "events": [{"title": "APAC HQ Established", "description": "Details", "source_ids": ["src-002"]}],
            "claims": [{"text": "Acme expands to Singapore", "source_ids": ["src-002"]}],
        }), 150, 60

    mock_llm = MockLLM(response_generator=mock_extract)
    sources = _create_sample_sources(4)
    context = ResearchContext(target_name="Acme Corp", meeting_objective="Expansion", time_window_days=30)

    events, claims = extract_events_and_claims(sources, context, mock_llm)

    assert events[0].source_ids == ["src-002"]
    assert claims[0].evidence[0].source_id == "src-002"
    assert "Acme Corp expanded operations" in claims[0].evidence[0].excerpt


# 11. Deterministic entity resolution and clustering (0 LLM calls!)
def test_deterministic_normalization_and_clustering(clean_tracker_and_cache):
    now = datetime.now(timezone.utc)
    mock_llm = MockLLM()  # Should NOT be called
    sources = [
        SourceRecord(
            source_id="src-pr1",
            url="https://www.businesswire.com/news/acme-q3",
            canonical_url="https://www.businesswire.com/news/acme-q3",
            title="Acme Corp Announces Q3 Results - BusinessWire",
            publisher="BusinessWire",
            snippet="Acme Corp announced Q3 revenue growth of 14%.",
            discovered_at=now,
            is_syndicated=False,
            syndication_confidence=0.0,
        ),
        SourceRecord(
            source_id="src-rep1",
            url="https://finance.yahoo.com/news/acme-q3",
            canonical_url="https://finance.yahoo.com/news/acme-q3",
            title="Acme Corp Announces Q3 Results",
            publisher="Yahoo Finance",
            snippet="Acme Corp announced Q3 revenue growth of 14%.",
            discovered_at=now,
            is_syndicated=False,
            syndication_confidence=0.0,
        ),
    ]

    norm_sources, origins = normalize(sources, mock_llm)
    # Zero LLM calls!
    assert mock_llm.call_count == 0
    # Yahoo article flagged as syndicated from BusinessWire PR
    assert any(s.is_syndicated for s in norm_sources)
    # One corporate PR origin
    assert any(not o.is_independent for o in origins)

    # Test deterministic event clustering
    events = [
        ExtractedEvent(
            event_id="e1",
            title="Acme Corp Announces Q3 Financial Results",
            description="Acme Corp released Q3 figures.",
            lifecycle_status="NEW",
            is_disputed=False,
            is_uncertain=False,
            discovered_at=now,
            source_ids=["src-pr1"],
        ),
        ExtractedEvent(
            event_id="e2",
            title="Acme Corp Announces Q3 Results",
            description="Acme Corp released detailed Q3 figures with margin metrics.",
            lifecycle_status="NEW",
            is_disputed=False,
            is_uncertain=False,
            discovered_at=now,
            source_ids=["src-rep1"],
        ),
    ]

    clustered = cluster_events(events, norm_sources, mock_llm)
    assert mock_llm.call_count == 0
    assert len(clustered) == 1
    assert "src-pr1" in clustered[0].source_ids and "src-rep1" in clustered[0].source_ids


# 12. Deterministic baseline and delta (0 LLM calls!)
def test_deterministic_baseline_and_delta(clean_tracker_and_cache):
    now = datetime.now(timezone.utc)
    mock_llm = MockLLM()
    from intelligence.contracts import EngineResultStatus, IntelligenceResult

    coverage_dummy = CoverageReport(
        planned_searches=1,
        executed_searches=1,
        failed_searches=0,
        time_window_days=30,
        origin_diversity_score=1.0,
        gaps=[],
        warnings=[],
    )

    current = IntelligenceResult(
        session_id="s1",
        job_id="j1",
        status=EngineResultStatus.COMPLETED,
        events=[
            ExtractedEvent(
                event_id="evt-new",
                title="New Event",
                description="New Event Description",
                lifecycle_status="NEW",
                is_disputed=False,
                is_uncertain=False,
                discovered_at=now,
            )
        ],
        claims=[],
        coverage=coverage_dummy,
    )
    baseline = ResearchBaseline(
        baseline_result_id="res-base",
        reviewed_at=now,
        known_event_ids=["evt-old"],
        known_claim_ids=[],
    )

    delta, versions = compute_delta(current, baseline, mock_llm)
    assert mock_llm.call_count == 0  # Zero calls!
    assert delta is not None
    assert delta.new_events == ["evt-new"]
    assert delta.no_material_change is False


# 13. Talking-point stress testing in a single batched call
def test_talking_point_stress_testing_batched(clean_tracker_and_cache):
    tracker, _ = clean_tracker_and_cache

    def mock_stress(sys, user, count):
        return json.dumps({
            "evaluations": [
                {
                    "point_index": 0,
                    "extracted_claims": ["Revenue grew 20%"],
                    "matched_claim_ids": ["clm-q3"],
                    "suggested_wording": "Acme reported 14% growth in Q3.",
                    "needs_more_research": False,
                },
                {
                    "point_index": 1,
                    "extracted_claims": ["Permanent CFO hired"],
                    "matched_claim_ids": [],
                    "suggested_wording": None,
                    "needs_more_research": True,
                },
            ]
        }), 250, 100

    mock_llm = MockLLM(response_generator=mock_stress)
    claims = [
        ExtractedClaim(
            claim_id="clm-q3",
            text="Q3 revenue grew 14%",
            assessment="CONTRADICTED",
            assessment_rationale="FT reports 14% contradicting 20% claim.",
            evidence=[],
            source_doc_count=1,
            independent_origin_count=1,
            volatility="LOW",
            is_stale=False,
            llm_confidence=0.9,
        )
    ]

    points = [
        "Acme Corp revenue grew 20% YoY",
        "A permanent CFO has been hired",
    ]

    res = run_stress_test(points, claims, [], mock_llm)
    # Exactly 1 call for all talking points!
    assert mock_llm.call_count == 1
    assert len(res.points) == 2
    assert res.points[0].suggested_wording == "Acme reported 14% growth in Q3."
    assert res.points[1].needs_more_research is True


# 14. Full pipeline execution targets 4–5 LLM requests!
def test_full_pipeline_execution_llm_call_count(clean_tracker_and_cache):
    tracker, _ = clean_tracker_and_cache

    def pipeline_mock(sys, user, count):
        if "research planner" in sys.lower():
            return json.dumps({
                "queries": ["Acme news", "Acme financials", "Acme leadership"],
                "entity_aliases": ["Acme Corp"],
                "time_filter": "past 30 days",
            }), 150, 50
        elif "investigative intelligence analyst" in sys.lower():
            return json.dumps({
                "events": [{"title": "Acme APAC Expansion", "description": "Singapore HQ planned", "source_ids": ["src-000"]}],
                "claims": [{"text": "Acme establishes Singapore office", "event_title": "Acme APAC Expansion", "source_ids": ["src-000"]}],
            }), 300, 100
        elif "evidence verification analyst" in sys.lower():
            return json.dumps({
                "assessments": [
                    {
                        "claim_id": "clm-mock",
                        "assessment": "SUPPORTED",
                        "rationale": "Directly confirmed.",
                        "supporting_source_ids": ["src-000"],
                    }
                ]
            }), 250, 80
        elif "executive intelligence analyst" in sys.lower():
            return json.dumps({
                "executive_briefing": "Executive briefing: Acme Corp is expanding to APAC. Margins remain stable."
            }), 200, 90
        elif "meeting communications" in sys.lower():
            return json.dumps({
                "evaluations": [
                    {
                        "point_index": 0,
                        "extracted_claims": ["Acme expansion"],
                        "matched_claim_ids": ["clm-mock"],
                        "suggested_wording": "Acme has announced APAC expansion.",
                        "needs_more_research": False,
                    }
                ]
            }), 220, 80
        return json.dumps({}), 10, 10

    mock_llm = MockLLM(response_generator=pipeline_mock)

    request = ResearchRequest(
        session_id="sess-opt-001",
        job_id="job-opt-001",
        context=ResearchContext(
            target_name="Acme Corp",
            meeting_objective="Review APAC Strategy",
            time_window_days=30,
            research_questions=["What is the status of APAC expansion?"],
            talking_points=["Acme is aggressively entering APAC"],
        ),
    )

    with patch("intelligence.engine.get_llm_provider", return_value=mock_llm):
        with patch("intelligence.engine.TavilySearchProvider") as mock_search_cls:
            mock_search_instance = MagicMock()
            mock_search_instance.search.return_value = _create_sample_sources(5)
            mock_search_cls.return_value = mock_search_instance

            result = _run_live_pipeline(request)

    # MEASUREMENT:
    # 1. Plan (1 call)
    # 2. Extract Events & Claims (1 call)
    # 3. Assess Claims (1 call)
    # 4. Generate Briefing (1 call)
    # 5. Stress Test (1 call)
    # Total calls: EXACTLY 5 calls!
    assert mock_llm.call_count == 5
    assert result.status == "COMPLETED"
    assert result.llm_usage is not None
    assert result.llm_usage.total_requests == 5
    assert result.llm_usage.stages["planning"] == 1
    assert result.llm_usage.stages["extraction"] == 1
    assert result.llm_usage.stages["assessment"] == 1
    assert result.llm_usage.stages["briefing"] == 1
    assert result.llm_usage.stages["stress_test"] == 1
    assert result.briefing_summary is not None

