"""Main intelligence engine entry point.

Orchestrates the optimized, quota-efficient research pipeline:
Stage A: Research Planning (1 LLM call)
Stage B: Search & Normalization (Deterministic, 0 LLM calls)
Stage C: Batched Event & Claim Extraction (1 LLM call for typical batch)
Stage D: Entity Resolution & Event Clustering (Deterministic, 0 LLM calls)
Stage E: Batched Evidence Assessment (1 LLM call)
Stage F: Deterministic Temporal Analysis & Delta (0 LLM calls)
Stage G: Briefing Generation (1 LLM call)
Stage H: Conditional Talking-Point Stress Testing (1 LLM call only if talking points submitted)

Total: ~4–6 LLM calls for a typical research run.
"""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import time
from typing import Optional

from intelligence.config import intelligence_settings
from intelligence.contracts import (
    CoverageReport,
    EngineResultStatus,
    IntelligenceResult,
    ResearchRequest,
    StressTestResult,
)
from intelligence.instrumentation import LLMUsageTracker, set_current_tracker
from intelligence.pipeline.assessor import assess_claims
from intelligence.pipeline.briefing import generate_briefing_summary
from intelligence.pipeline.clusterer import cluster_events
from intelligence.pipeline.coverage import build_report
from intelligence.pipeline.delta import compute as compute_delta
from intelligence.pipeline.extractor import extract_events_and_claims
from intelligence.pipeline.normalizer import normalize
from intelligence.pipeline.planner import plan
from intelligence.pipeline.stress_test import run as run_stress_test
from intelligence.providers.base import LLMParseError, QuotaExhaustedError, SearchProviderError
from intelligence.providers.llm import get_llm_provider
from intelligence.providers.tavily import TavilySearchProvider

logger = logging.getLogger("changeradar.intelligence.engine")

_FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_fixture_result(session_id: str, job_id: str) -> IntelligenceResult:
    data = json.loads((_FIXTURES_DIR / "sample_result.json").read_text(encoding="utf-8"))
    data["session_id"] = session_id
    data["job_id"] = job_id
    res = IntelligenceResult.model_validate(data)
    # Ensure provider metadata records fixture mode
    res.provider_metadata["mode"] = "fixture"
    return res


def _run_live_pipeline(request: ResearchRequest) -> IntelligenceResult:
    warnings: list[str] = []
    tracker = LLMUsageTracker(run_id=request.job_id)
    set_current_tracker(tracker)

    search_provider = TavilySearchProvider()
    llm_provider = get_llm_provider()

    # 1. Stage A: Plan (1 LLM call)
    research_plan = plan(request.context, llm_provider)

    # 2. Stage B: Search (Tavily search API - parallelized with bounded concurrency)
    all_raw_sources = []
    executed = 0
    failed = 0

    # Deduplicate queries while preserving order
    unique_queries: list[str] = []
    seen_queries: set[str] = set()
    for q in research_plan.queries:
        q_clean = q.strip()
        if q_clean and q_clean.lower() not in seen_queries:
            seen_queries.add(q_clean.lower())
            unique_queries.append(q_clean)

    query_results: dict[str, list] = {}

    def _exec_search(q: str):
        return q, search_provider.search(q, request.context)

    if unique_queries:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        max_workers = min(4, max(1, len(unique_queries)))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_query = {executor.submit(_exec_search, q): q for q in unique_queries}
            for future in as_completed(future_to_query):
                q = future_to_query[future]
                try:
                    _, results = future.result()
                    query_results[q] = results
                    executed += 1
                except SearchProviderError as exc:
                    failed += 1
                    warnings.append(f"Search failed for query '{q}': {exc}")
                    logger.warning(f"Search failed for '{q}': {exc}")
                except Exception as exc:
                    failed += 1
                    warnings.append(f"Unexpected search error for '{q}': {exc}")
                    logger.warning(f"Unexpected search error for '{q}': {exc}")

        # Assemble in predictable deterministic query order
        for q in unique_queries:
            if q in query_results:
                all_raw_sources.extend(query_results[q])

    if not all_raw_sources:
        warnings.append("No sources retrieved — search queries returned empty results.")
        usage_rep = tracker.get_summary()
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
                gaps=["No sources retrieved in search scope."],
                warnings=warnings,
            ),
            warnings=warnings,
            provider_metadata=_provider_metadata(tracker),
            llm_usage=usage_rep,
        )

    # 3. Stage B & D: Source normalization and origin clustering (0 LLM calls - Deterministic)
    try:
        sources, origins = normalize(all_raw_sources, llm_provider)
    except Exception as exc:
        logger.warning(f"Normalizer failed, falling back to raw sources: {exc}")
        warnings.append(f"Source normalization warning: {exc}")
        sources = all_raw_sources
        origins = []

    # 4. Stage C: Batched Event and Claim Extraction (1 LLM call for typical batch)
    try:
        events, claims = extract_events_and_claims(sources, request.context, llm_provider)
    except QuotaExhaustedError as exc:
        logger.error(f"Quota exhausted during event extraction: {exc}")
        warnings.append(f"Gemini API quota exhausted during extraction: {exc}")
        events, claims = [], []
    except Exception as exc:
        logger.warning(f"Event and claim extraction failed: {exc}")
        warnings.append(f"Extraction failed: {exc}")
        events, claims = [], []

    # 5. Stage D: Event Clustering (0 LLM calls - Deterministic)
    try:
        events = cluster_events(events, sources, llm_provider)
    except Exception as exc:
        logger.warning(f"Event clustering encountered error: {exc}")
        warnings.append(f"Event clustering warning: {exc}")

    # 6. Stage E: Batched Claim Assessment (1 LLM call)
    try:
        claims = assess_claims(claims, sources, origins, llm_provider)
    except QuotaExhaustedError as exc:
        logger.error(f"Quota exhausted during claim assessment: {exc}")
        warnings.append(f"Gemini API quota exhausted during assessment: {exc}")
    except Exception as exc:
        logger.warning(f"Claim assessment failed: {exc}")
        warnings.append(f"Claim assessment failed: {exc}")

    # 7. Coverage report & gap detection (0 LLM calls - Deterministic)
    coverage = build_report(
        plan=research_plan,
        executed=executed,
        failed=failed,
        sources=sources,
        origins=origins,
        context=request.context,
        claims=claims,
        events=events,
        llm=llm_provider,
    )

    # 8. Stage F: Temporal Analysis & Delta (0 LLM calls - Deterministic)
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
                provider_metadata=_provider_metadata(tracker),
            )
            delta, event_versions = compute_delta(current_partial, request.baseline, llm_provider)
        except Exception as exc:
            logger.warning(f"Delta computation failed: {exc}")
            warnings.append(f"Delta computation warning: {exc}")

    # 9. Stage G: Briefing Generation (1 LLM call)
    briefing_text = None
    try:
        briefing_text = generate_briefing_summary(
            request.context, events, claims, coverage, delta, llm_provider
        )
    except Exception as exc:
        logger.warning(f"Briefing generation encountered error: {exc}")
        warnings.append(f"Briefing generation fallback used: {exc}")

    # 10. Stage H: Talking-point Stress Testing (Conditional: 1 LLM call ONLY if talking points submitted)
    stress_test: StressTestResult | None = None
    if request.context.talking_points:
        try:
            stress_test = run_stress_test(
                request.context.talking_points, claims, sources, llm_provider
            )
        except QuotaExhaustedError as exc:
            logger.error(f"Quota exhausted during stress test: {exc}")
            warnings.append(f"Gemini API quota exhausted during stress test: {exc}")
        except Exception as exc:
            logger.warning(f"Stress test failed: {exc}")
            warnings.append(f"Stress test warning: {exc}")

    status = EngineResultStatus.PARTIAL if (failed > 0 or warnings) else EngineResultStatus.COMPLETED
    usage_report = tracker.get_summary()

    return IntelligenceResult(
        session_id=request.session_id,
        job_id=request.job_id,
        status=status,
        briefing_summary=briefing_text,
        sources=sources,
        origins=origins,
        events=events,
        event_versions=event_versions,
        claims=claims,
        coverage=coverage,
        delta=delta,
        stress_test=stress_test,
        warnings=warnings,
        provider_metadata=_provider_metadata(tracker),
        llm_usage=usage_report,
    )


def _provider_metadata(tracker: Optional[LLMUsageTracker] = None) -> dict:
    meta = {
        "search_provider": "tavily",
        "llm_provider": intelligence_settings.LLM_PROVIDER,
        "llm_model": intelligence_settings.LLM_MODEL,
        "run_at": datetime.now(timezone.utc).isoformat(),
    }
    if tracker:
        summary = tracker.get_summary()
        meta["llm_usage"] = summary.model_dump()
    return meta


def run_intelligence_engine(request: ResearchRequest) -> IntelligenceResult:
    """Main entry point called by the backend worker.

    Returns IntelligenceResult — never raises.
    """
    start = time.perf_counter()
    logger.info(
        f"Engine starting — session={request.session_id} job={request.job_id} "
        f"provider={intelligence_settings.LLM_PROVIDER} model={intelligence_settings.LLM_MODEL} "
        f"fixture={intelligence_settings.USE_FIXTURE_MODE}"
    )

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
