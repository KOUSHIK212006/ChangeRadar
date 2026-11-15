"""Coverage report builder.

Computes search coverage statistics and uses LLM to identify topic gaps.
"""

import json
import logging

from intelligence.contracts import (
    CoverageReport,
    ResearchContext,
    SourceOriginRecord,
    SourceRecord,
)
from intelligence.pipeline.planner import ResearchPlan
from intelligence.providers.base import LLMParseError, LLMProvider

logger = logging.getLogger("changeradar.intelligence.pipeline.coverage")

GAP_SYSTEM = (
    "You are a research analyst. Given a list of research questions and retrieved sources, "
    "identify which questions or topics were not adequately addressed. "
    "Return only valid JSON."
)


def _origin_diversity_score(origins: list[SourceOriginRecord]) -> float:
    if not origins:
        return 0.0
    independent = sum(1 for o in origins if o.is_independent)
    return round(independent / len(origins), 2)


def _source_types(sources: list[SourceRecord]) -> list[str]:
    """Infer rough source types from publisher names."""
    types: set[str] = set()
    press_release_keywords = {"businesswire", "prnewswire", "globenewswire", "accesswire"}
    filing_keywords = {"sec.gov", "edgar", "regulatory"}
    for s in sources:
        pub = s.publisher.lower()
        if any(k in pub for k in press_release_keywords):
            types.add("press_release")
        elif any(k in pub for k in filing_keywords):
            types.add("filing")
        else:
            types.add("news")
    return sorted(types)


def _detect_gaps(
    context: ResearchContext,
    sources: list[SourceRecord],
    llm: LLMProvider,
) -> list[str]:
    if not context.research_questions:
        return []

    source_summaries = [
        {"title": s.title, "snippet": s.snippet[:200]}
        for s in sources[:20]
    ]
    user_prompt = (
        f"Research questions:\n{json.dumps(context.research_questions)}\n\n"
        f"Sources retrieved:\n{json.dumps(source_summaries, indent=2)}\n\n"
        'Return JSON: {"gaps": ["question or topic not covered", ...]}\n'
        "Only list questions that were genuinely not addressed by the sources."
    )

    try:
        raw = llm.complete(GAP_SYSTEM, user_prompt)
        data = json.loads(raw)
        return data.get("gaps", [])
    except (LLMParseError, Exception) as exc:
        logger.warning(f"Gap detection failed: {exc}")
        return []


def build_report(
    plan: ResearchPlan,
    executed: int,
    failed: int,
    sources: list[SourceRecord],
    origins: list[SourceOriginRecord],
    context: ResearchContext,
    llm: LLMProvider,
) -> CoverageReport:
    warnings: list[str] = []

    if not sources:
        warnings.append("No sources retrieved.")
    if failed > 0:
        warnings.append(f"{failed} search(es) failed.")

    independent_origins = [o for o in origins if o.is_independent]
    if origins and len(independent_origins) <= 1:
        warnings.append("All sources may originate from a single origin — treat as 1 independent confirmation.")

    gaps = _detect_gaps(context, sources, llm)

    return CoverageReport(
        planned_searches=len(plan.queries),
        executed_searches=executed,
        failed_searches=failed,
        time_window_days=context.time_window_days,
        source_types_found=_source_types(sources),
        origin_diversity_score=_origin_diversity_score(origins),
        gaps=gaps,
        warnings=warnings,
    )
