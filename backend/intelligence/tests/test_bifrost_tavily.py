"""Tests for mandatory Tavily search provider and Bifrost LLM gateway integrations.

Verifies:
1. Tavily API client requests, URL normalization, publication date parsing, rate limits, and retries.
2. Bifrost OpenAI-compatible gateway request formatting, header routing (x-goog-api-key),
   structured output validation, error classification, quota handling, and telemetry.
3. Centralized factory routing and intelligence engine integration.
"""

from datetime import datetime, timezone
import json
from unittest.mock import MagicMock, patch
import pytest
import httpx

from intelligence.config import intelligence_settings
from intelligence.contracts import (
    EngineResultStatus,
    IntelligenceResult,
    ResearchContext,
    ResearchRequest,
    SourceRecord,
)
from intelligence.instrumentation import LLMUsageTracker, set_current_tracker
from intelligence.providers.base import (
    LLMParseError,
    PermanentLLMError,
    QuotaExhaustedError,
    SearchProviderError,
    TransientLLMError,
)
from intelligence.providers.llm import (
    BifrostLLMProvider,
    GeminiLLMProvider,
    get_llm_provider,
)
from intelligence.providers.tavily import (
    TavilySearchProvider,
    _parse_publisher,
    _source_id,
    _strip_utm,
)


# ==============================================================================
# A. Tavily Search Provider Tests
# ==============================================================================

def test_tavily_strip_utm_and_source_id():
    """Verify UTM parameters are stripped and source IDs are deterministic."""
    raw_url = "https://www.reuters.com/business/tech?utm_source=twitter&utm_medium=social#heading"
    clean = _strip_utm(raw_url)
    assert clean == "https://www.reuters.com/business/tech#heading"
    assert "utm_source" not in clean

    s_id_1 = _source_id(clean)
    s_id_2 = _source_id(clean)
    assert s_id_1 == s_id_2
    assert len(s_id_1) == 16

    assert _parse_publisher("https://www.bloomberg.com/news") == "bloomberg.com"


def test_tavily_missing_api_key_raises_error():
    """Verify missing API key raises SearchProviderError immediately."""
    provider = TavilySearchProvider(api_key="")
    context = ResearchContext(target_name="Acme Corp", meeting_objective="Partnership evaluation")
    with pytest.raises(SearchProviderError, match="TAVILY_API_KEY is not configured"):
        provider.search("Acme Corp acquisitions", context)


def test_tavily_search_success_and_normalization():
    """Verify successful Tavily search parses results and normalizes into SourceRecord schema."""
    fake_response = {
        "results": [
            {
                "title": "Acme Corp Announces Next-Gen AI Chip",
                "url": "https://techcrunch.com/2026/01/15/acme-ai-chip/?utm_source=rss",
                "content": "Acme Corp today revealed its revolutionary new neural processing unit...",
                "published_date": "2026-01-15T14:30:00Z",
                "score": 0.98,
            },
            {
                "title": "Undated Acme Industry Overview",
                "url": "https://venturebeat.com/ai/acme-overview",
                "content": "A comprehensive deep dive into Acme's business model...",
                "published_date": None,
                "score": 0.85,
            },
        ]
    }

    provider = TavilySearchProvider(api_key="tvly-mock-test-key", max_results=5)
    context = ResearchContext(target_name="Acme Corp", meeting_objective="Partnership evaluation")

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = fake_response
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.post", return_value=mock_resp) as mock_post:
        records = provider.search("Acme Corp news", context)

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["api_key"] == "tvly-mock-test-key"
        assert call_kwargs["json"]["query"] == "Acme Corp news"
        assert call_kwargs["json"]["max_results"] == 5

    assert len(records) == 2
    r0 = records[0]
    assert isinstance(r0, SourceRecord)
    assert r0.title == "Acme Corp Announces Next-Gen AI Chip"
    assert r0.publisher == "techcrunch.com"
    assert "utm_source" not in r0.canonical_url
    assert r0.published_at == datetime(2026, 1, 15, 14, 30, tzinfo=timezone.utc)
    assert "revolutionary" in r0.snippet

    r1 = records[1]
    assert r1.published_at is None
    assert r1.publisher == "venturebeat.com"


def test_tavily_rate_limit_retry_and_recovery():
    """Verify HTTP 429 triggers exponential backoff retry and succeeds upon recovery."""
    provider = TavilySearchProvider(
        api_key="tvly-test-key",
        max_retries=2,
        backoff_base=1.1,
        backoff_max=0.5,
    )
    context = ResearchContext(target_name="Acme Corp", meeting_objective="Partnership evaluation")

    resp_429 = MagicMock(spec=httpx.Response)
    resp_429.status_code = 429
    resp_429.headers = {"Retry-After": "0.01"}
    resp_429.text = "Rate limit reached"

    resp_200 = MagicMock(spec=httpx.Response)
    resp_200.status_code = 200
    resp_200.json.return_value = {"results": [{"title": "Success", "url": "https://example.com", "content": "Text"}]}
    resp_200.raise_for_status = MagicMock()

    with patch("httpx.post", side_effect=[resp_429, resp_200]) as mock_post, \
         patch("time.sleep") as mock_sleep:
        records = provider.search("Acme", context)
        assert len(records) == 1
        assert mock_post.call_count == 2
        mock_sleep.assert_called_once()


def test_tavily_auth_failure_no_retry():
    """Verify HTTP 401/403 fails immediately without wasteful retries."""
    provider = TavilySearchProvider(api_key="tvly-invalid-key", max_retries=3)
    context = ResearchContext(target_name="Acme Corp", meeting_objective="Partnership evaluation")

    resp_401 = MagicMock(spec=httpx.Response)
    resp_401.status_code = 401
    resp_401.text = "Unauthorized: Invalid API key"

    with patch("httpx.post", return_value=resp_401) as mock_post:
        with pytest.raises(SearchProviderError, match="Tavily authentication failed"):
            provider.search("Acme", context)
        assert mock_post.call_count == 1


# ==============================================================================
# B. Bifrost Centralized LLM Gateway Tests
# ==============================================================================

def test_bifrost_provider_initialization():
    """Verify Bifrost provider resolves configuration, gateway URL, and model correctly."""
    provider = BifrostLLMProvider(
        base_url="http://bifrost.internal:8080/",
        api_key="bf-vk-test-token",
        upstream_key="gemini-test-secret",
        model="gemini/gemini-2.0-flash",
    )
    assert provider._base_url == "http://bifrost.internal:8080"
    assert provider.provider_name == "bifrost"
    assert provider._model == "gemini/gemini-2.0-flash"


def test_bifrost_chat_completion_success():
    """Verify Bifrost routes OpenAI-format payload and forwards x-goog-api-key."""
    provider = BifrostLLMProvider(
        base_url="http://localhost:8080",
        api_key="bf-gateway-vk",
        upstream_key="gemini-upstream-secret",
        model="gemini/gemini-1.5-flash",
        timeout=15,
        max_retries=1,
    )

    tracker = LLMUsageTracker(run_id="test-run")
    set_current_tracker(tracker)

    mock_resp_json = {
        "id": "chatcmpl-bifrost-12345",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": '{"summary": "ChangeRadar successfully queried Bifrost", "score": 95}',
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 42,
            "completion_tokens": 18,
            "total_tokens": 60,
        },
    }

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_resp_json
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.post", return_value=mock_resp) as mock_post:
        content = provider.complete("You are a research analyst.", "Analyze Acme Corp.")

        assert json.loads(content)["score"] == 95
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "http://localhost:8080/v1/chat/completions"

        # Verify headers include gateway virtual key and upstream key
        headers = kwargs["headers"]
        assert headers["Authorization"] == "Bearer bf-gateway-vk"
        assert headers["x-bf-vk"] == "bf-gateway-vk"
        assert headers["x-goog-api-key"] == "gemini-upstream-secret"

        # Verify payload structure
        payload = kwargs["json"]
        assert payload["model"] == "gemini/gemini-1.5-flash"
        assert payload["response_format"] == {"type": "json_object"}
        assert len(payload["messages"]) == 2

    # Verify telemetry
    summary = tracker.get_summary()
    assert summary.total_requests == 1
    assert summary.total_input_tokens == 42
    assert summary.total_output_tokens == 18


def test_bifrost_rate_limit_retry():
    """Verify Bifrost 429 triggers exponential backoff retry and records QuotaExhausted telemetry."""
    provider = BifrostLLMProvider(
        base_url="http://localhost:8080",
        api_key="bf-test-key",
        upstream_key="gemini-key",
        max_retries=2,
    )

    tracker = LLMUsageTracker(run_id="test-retry")
    set_current_tracker(tracker)

    resp_429 = MagicMock(spec=httpx.Response)
    resp_429.status_code = 429
    resp_429.headers = {"Retry-After": "0.01"}
    resp_429.text = '{"error": {"message": "Rate limit exceeded"}}'

    resp_200 = MagicMock(spec=httpx.Response)
    resp_200.status_code = 200
    resp_200.json.return_value = {
        "choices": [{"message": {"content": '{"result": "ok"}'}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 10},
    }
    resp_200.raise_for_status = MagicMock()

    with patch("httpx.post", side_effect=[resp_429, resp_200]) as mock_post, \
         patch("time.sleep"):
        res = provider.complete("System prompt", "User prompt")
        assert json.loads(res)["result"] == "ok"
        assert mock_post.call_count == 2


def test_bifrost_permanent_auth_error():
    """Verify 401/403 from Bifrost raises PermanentLLMError immediately."""
    provider = BifrostLLMProvider(
        base_url="http://localhost:8080",
        api_key="invalid-gateway-token",
        max_retries=3,
    )

    resp_401 = MagicMock(spec=httpx.Response)
    resp_401.status_code = 401
    resp_401.text = "Invalid gateway token"

    with patch("httpx.post", return_value=resp_401) as mock_post:
        with pytest.raises(PermanentLLMError, match="Bifrost Gateway Auth Error"):
            provider.complete("System", "User")
        assert mock_post.call_count == 1


def test_bifrost_empty_choices_raises_parse_error():
    """Verify empty choices list from Bifrost raises LLMParseError."""
    provider = BifrostLLMProvider(
        base_url="http://localhost:8080",
        api_key="valid-key",
        max_retries=0,
    )

    resp_empty = MagicMock(spec=httpx.Response)
    resp_empty.status_code = 200
    resp_empty.json.return_value = {"choices": []}
    resp_empty.raise_for_status = MagicMock()

    with patch("httpx.post", return_value=resp_empty):
        with pytest.raises(LLMParseError, match="empty choices list"):
            provider.complete("System", "User")


def test_bifrost_malformed_json_content():
    """Verify non-JSON response content raises LLMParseError."""
    provider = BifrostLLMProvider(
        base_url="http://localhost:8080",
        api_key="valid-key",
        max_retries=0,
    )

    resp_bad = MagicMock(spec=httpx.Response)
    resp_bad.status_code = 200
    resp_bad.json.return_value = {
        "choices": [{"message": {"content": "This is raw text, not valid JSON"}}],
    }
    resp_bad.raise_for_status = MagicMock()

    with patch("httpx.post", return_value=resp_bad):
        with pytest.raises(LLMParseError, match="not valid JSON"):
            provider.complete("System", "User")


# ==============================================================================
# C. Factory & Pipeline Gateway Verification
# ==============================================================================

def test_get_llm_provider_resolves_bifrost_by_default():
    """Verify get_llm_provider() instantiates BifrostLLMProvider by default."""
    with patch.object(intelligence_settings, "LLM_PROVIDER", "bifrost"), \
         patch.object(intelligence_settings, "BIFROST_BASE_URL", "http://gateway.corp:8080"), \
         patch.object(intelligence_settings, "BIFROST_MODEL", "gemini/gemini-1.5-flash"):
        provider = get_llm_provider()
        assert isinstance(provider, BifrostLLMProvider)
        assert provider.provider_name == "bifrost"
        assert provider._base_url == "http://gateway.corp:8080"
        assert provider._model == "gemini/gemini-1.5-flash"


def test_get_llm_provider_backward_compatibility():
    """Verify factory still supports explicit gemini/groq provider requests."""
    p_gemini = get_llm_provider(provider_name="gemini")
    assert isinstance(p_gemini, GeminiLLMProvider)
    assert p_gemini.provider_name == "gemini"


def test_engine_metadata_records_bifrost_gateway():
    """Verify engine records gateway: bifrost and gateway_url in provider_metadata."""
    from intelligence.engine import _provider_metadata

    with patch.object(intelligence_settings, "LLM_PROVIDER", "bifrost"), \
         patch.object(intelligence_settings, "BIFROST_BASE_URL", "http://localhost:8080"), \
         patch.object(intelligence_settings, "BIFROST_MODEL", "gemini/gemini-1.5-flash"):
        meta = _provider_metadata()
        assert meta["search_provider"] == "tavily"
        assert meta["llm_provider"] == "bifrost"
        assert meta["gateway"] == "bifrost"
        assert meta["gateway_url"] == "http://localhost:8080"
        assert meta["llm_model"] == "gemini/gemini-1.5-flash"


def test_live_pipeline_integration_with_bifrost_and_tavily():
    """Verify end-to-end execution of live research pipeline routing through Bifrost and Tavily."""
    from intelligence.engine import _run_live_pipeline

    req = ResearchRequest(
        session_id="test-session-bifrost",
        job_id="test-job-bifrost",
        context=ResearchContext(
            target_name="Acme Robotics",
            meeting_objective="Pre-investment due diligence",
            target_domain="Hardware & Robotics",
            time_window_days=30,
        ),
    )

    fake_search_records = [
        SourceRecord(
            source_id="src001",
            url="https://techcrunch.com/2026/01/10/acme-robotics-series-b",
            canonical_url="https://techcrunch.com/2026/01/10/acme-robotics-series-b",
            title="Acme Robotics Closes $50M Series B",
            publisher="techcrunch.com",
            snippet="Acme Robotics raised $50M led by Horizon Ventures to accelerate factory automation.",
            published_at=datetime(2026, 1, 10, tzinfo=timezone.utc),
            discovered_at=datetime.now(timezone.utc),
        )
    ]

    # Mock stage responses from Bifrost
    stage_responses = {
        "plan": json.dumps({
            "queries": ["Acme Robotics funding", "Acme Robotics factory automation"],
            "entity_aliases": ["Acme Robotics", "Acme"],
            "time_filter": "last 30 days",
        }),
        "extract": json.dumps({
            "events": [{
                "title": "Series B Funding of $50M",
                "description": "Acme Robotics secured $50M in Series B round.",
                "lifecycle_status": "NEW",
                "is_disputed": False,
                "is_uncertain": False,
                "event_at": "2026-01-10T00:00:00Z",
                "source_ids": ["src001"],
            }],
            "claims": [{
                "text": "Acme Robotics raised $50M led by Horizon Ventures",
                "event_title": "Series B Funding of $50M",
                "volatility": "LOW",
                "source_ids": ["src001"],
            }]
        }),
        "assess": json.dumps({
            "assessments": [{
                "claim_id": "placeholder",
                "confidence_score": 0.95,
                "verification_status": "VERIFIED",
                "rationale": "Directly confirmed by financial reporting",
                "corroboration_type": "SINGLE_ORIGIN_VERIFIED",
            }]
        }),
        "briefing": json.dumps({
            "executive_summary": "Acme Robotics is in strong growth mode following a $50M Series B.",
            "key_developments": ["Secured $50M Series B led by Horizon Ventures."],
            "strategic_implications": ["Rapidly scaling factory automation solutions."],
            "risks_and_watchouts": ["Execution risk in market deployment."],
            "recommended_questions": ["What is the planned timeline for factory rollouts?"],
        }),
    }

    class MockBifrostClient(BifrostLLMProvider):
        def _call_api(self, system_prompt: str, user_prompt: str):
            sp = system_prompt.lower()
            up = user_prompt.lower()
            if "query generation" in sp or "queries" in up or "planning" in sp:
                return stage_responses["plan"], 50, 20
            elif "investigative intelligence" in sp or "events" in up and "claims" in up:
                return stage_responses["extract"], 120, 80
            elif "assessment" in sp or "assess" in up or "corroborat" in sp:
                return stage_responses["assess"], 90, 40
            else:
                return stage_responses["briefing"], 200, 150

    mock_llm = MockBifrostClient(
        base_url="http://localhost:8080",
        api_key="bf-test-vk",
        upstream_key="gemini-test-key",
    )

    with patch("intelligence.engine.TavilySearchProvider.search", return_value=fake_search_records), \
         patch("intelligence.engine.get_llm_provider", return_value=mock_llm), \
         patch.object(intelligence_settings, "TAVILY_API_KEY", "tvly-key"), \
         patch.object(intelligence_settings, "BIFROST_API_KEY", "bf-key"), \
         patch.object(intelligence_settings, "GEMINI_API_KEY", "gemini-key"), \
         patch.object(intelligence_settings, "LLM_PROVIDER", "bifrost"):
        result = _run_live_pipeline(req)

        assert isinstance(result, IntelligenceResult)
        assert result.status == EngineResultStatus.COMPLETED
        assert len(result.sources) == 1
        assert len(result.events) == 1
        assert len(result.claims) == 1
        assert result.provider_metadata["gateway"] == "bifrost"
        assert result.provider_metadata["search_provider"] == "tavily"
        assert result.provider_metadata["llm_provider"] == "bifrost"
        assert result.briefing_summary is not None
        assert "Acme Robotics" in result.briefing_summary


def test_live_pipeline_reports_missing_credentials_diagnostics():
    """Verify live pipeline adds explicit warnings when mandatory credentials are empty."""
    from intelligence.engine import _run_live_pipeline

    req = ResearchRequest(
        session_id="test-missing-creds",
        job_id="test-job-missing-creds",
        context=ResearchContext(
            target_name="Acme Robotics",
            meeting_objective="Test",
        ),
    )

    with patch.object(intelligence_settings, "TAVILY_API_KEY", ""), \
         patch.object(intelligence_settings, "LLM_PROVIDER", "bifrost"), \
         patch.object(intelligence_settings, "BIFROST_BASE_URL", "http://localhost:8080"), \
         patch.object(intelligence_settings, "BIFROST_API_KEY", ""), \
         patch.object(intelligence_settings, "GEMINI_API_KEY", ""):
        result = _run_live_pipeline(req)

        # Result warnings should clearly report missing Tavily and Bifrost credentials
        assert any("TAVILY_API_KEY is not configured" in w for w in result.warnings)
        assert any("Neither BIFROST_API_KEY" in w for w in result.warnings)

