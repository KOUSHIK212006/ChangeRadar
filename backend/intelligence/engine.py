"""Main intelligence engine entry point.

This is the only function the backend worker calls.
Input: ResearchRequest (validated by the worker)
Output: IntelligenceResult (validated Pydantic model)

Never raises — always returns an IntelligenceResult with appropriate status.
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from intelligence.config import intelligence_settings
from intelligence.contracts import (
    CoverageReport,
    EngineResultStatus,
    IntelligenceResult,
    ResearchRequest,
    StressTestResult,
)
from intelligence.pipeline.assessor import assess_claims
from intelligence.pipeline.clusterer import cluster_events
from intelligence.pipeline.coverage import build_report
from intelligence.pipeline.delta import compute as compute_delta
from intelligence.pipeline.extractor import extract_claims, extract_events
from intelligence.pipeline.normalizer import normalize
from intelligence.pipeline.planner import plan
from intelligence.pipeline.stress_test import run as run_stress_test
from intelligence.providers.base import LLMParseError, SearchProviderError
from intelligence.providers.llm import GroqLLMProvider
from intelligence.providers.tavily import TavilySearchProvider

logger = logging.getLogger("changeradar.intelligence.engine")

_FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_fixture_result(session_id: str, job_id: str) -> IntelligenceResult:
    data = json.loads((_FIXTURES_DIR / "sample_result.json").read_text())
    data["session_id"] = session_id
    data["job_id"] = job_id
    return IntelligenceResult.model_validate(data)


def _run_live_pipeline(request: ResearchRequest) -> IntelligenceResult:
    warnings: list[str] = []
    search_provider = TavilySearchProvider()
    llm_provider = GroqLLMProvider()

    # 1. Plan
    research_plan = plan(request.context, llm_provider)

    # 2. Search
    all_raw_sources = []
    executed = 0
    failed = 0
    for query in research_plan.queries:
        try:
            results = search_provider.search(query, request.context)
            all_raw_sources.extend(results)
            executed += 1
        except SearchProviderError as exc:
            failed += 1
            warnings.append(f"Search failed for query '{query}': {exc}")
            logger.warning(f"Search failed: {exc}")

    if not all_raw_sources:
        warnings.append("No sources retrieved — all searches failed or returned empty results.")
        return IntelligenceResult(
            session_id=request.session_id,
            job_id=request.job_id,
            status=EngineResultStatus.PARTIAL,
            coverage=CoverageReport(
                planned_searches=len(research_plan.queries),
                executed_searches=executed,
                failed_searches=failed,
                time_window_days=request.context.time_window_days,
                origin_diversity_score=0.0,
                gaps=["No sources retrieved"],
                warnings=warnings,
            ),
            warnings=warnings,
            provider_metadata=_provider_metadata(),
        )

    # 3. Normalize sources and group origins
    try:
        sources, origins = normalize(all_raw_sources, llm_provider)
    except Exception as exc:
        logger.warning(f"Normalizer failed, using raw sources: {exc}")
        warnings.append(f"Source normalization failed: {exc}")
        sources = all_raw_sources
        origins = []

    # 4. Extract events
    try:
        events = extract_events(sources, request.context, llm_provider)
    except Exception as exc:
        logger.warning(f"Event extraction failed: {exc}")
        warnings.append(f"Event extraction failed: {exc}")
        events = []

    # 5. Extract claims
    try:
        claims = extract_claims(events, sources, llm_provider)
    except Exception as exc:
        logger.warning(f"Claim extraction failed: {exc}")
        warnings.append(f"Claim extraction failed: {exc}")
        claims = []

    # 6. Cluster events
    try:
        events = cluster_events(events, sources, llm_provider)
    except Exception as exc:
        logger.warning(f"Event clustering failed: {exc}")
        warnings.append(f"Event clustering failed: {exc}")

    # 7. Assess claims
    try:
        claims = assess_claims(claims, sources, origins, llm_provider)
    except Exception as exc:
        logger.warning(f"Claim assessment failed: {exc}")
        warnings.append(f"Claim assessment failed: {exc}")

    # 8. Coverage report
    coverage = build_report(
        plan=research_plan,
        executed=executed,
        failed=failed,
        sources=sources,
        origins=origins,
        context=request.context,
        llm=llm_provider,
    )

    # 9. Delta + event versions
    delta = None
    event_versions = []
    if request.baseline:
        try:
            current_partial = IntelligenceResult(
                session_id=request.session_id,
                job_id=request.job_id,
                status=EngineResultStatus.COMPLETED,
                sources=sources,
                origins=origins,
                events=events,
                claims=claims,
                coverage=coverage,
                warnings=warnings,
                provider_metadata=_provider_metadata(),
            )
            delta, event_versions = compute_delta(current_partial, request.baseline, llm_provider)
        except Exception as exc:
            logger.warning(f"Delta computation failed: {exc}")
            warnings.append(f"Delta computation failed: {exc}")

    # 10. Stress test
    stress_test: StressTestResult | None = None
    if request.context.talking_points:
        try:
            stress_test = run_stress_test(request.context.talking_points, claims, sources, llm_provider)
        except Exception as exc:
            logger.warning(f"Stress test failed: {exc}")
            warnings.append(f"Stress test failed: {exc}")

    status = EngineResultStatus.PARTIAL if (failed > 0 or warnings) else EngineResultStatus.COMPLETED

    return IntelligenceResult(
        session_id=request.session_id,
        job_id=request.job_id,
        status=status,
        sources=sources,
        origins=origins,
        events=events,
        event_versions=event_versions,
        claims=claims,
        coverage=coverage,
        delta=delta,
        stress_test=stress_test,
        warnings=warnings,
        provider_metadata=_provider_metadata(),
    )


def _provider_metadata() -> dict:
    return {
        "search_provider": "tavily",
        "llm_provider": "groq",
        "llm_model": intelligence_settings.LLM_MODEL,
        "run_at": datetime.now(timezone.utc).isoformat(),
    }


def run_intelligence_engine(request: ResearchRequest) -> IntelligenceResult:
    """Main entry point called by the backend worker.

    Returns IntelligenceResult — never raises.
    """
    start = time.perf_counter()
    logger.info(f"Engine starting — session={request.session_id} job={request.job_id} fixture={intelligence_settings.USE_FIXTURE_MODE}")

    try:
        if intelligence_settings.USE_FIXTURE_MODE:
            result = _load_fixture_result(request.session_id, request.job_id)
        else:
            result = _run_live_pipeline(request)
    except Exception as exc:
        logger.exception(f"Engine encountered an unrecoverable error: {exc}")
        result = IntelligenceResult(
            session_id=request.session_id,
            job_id=request.job_id,
            status=EngineResultStatus.FAILED,
            coverage=CoverageReport(
                planned_searches=0,
                executed_searches=0,
                failed_searches=0,
                time_window_days=request.context.time_window_days,
                origin_diversity_score=0.0,
                gaps=[],
                warnings=[str(exc)],
            ),
            warnings=[str(exc)],
            provider_metadata=_provider_metadata(),
        )

    elapsed = (time.perf_counter() - start) * 1000
    logger.info(f"Engine finished — status={result.status} duration={elapsed:.0f}ms")
    return result
