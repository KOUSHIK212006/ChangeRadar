"""Coverage report builder — deterministic research audit and gap analysis.

Calculates search coverage statistics, origin diversity scores, source type breakdown,
and detects uncovered research questions without LLM call overhead.
"""

from typing import List, Optional, Set

from intelligence.contracts import (
    CoverageReport,
    ExtractedClaim,
    ExtractedEvent,
    ResearchContext,
    SourceOriginRecord,
    SourceRecord,
)
from intelligence.pipeline.planner import ResearchPlan
from intelligence.providers.base import LLMProvider

PRESS_RELEASE_DOMAINS = {"businesswire", "prnewswire", "globenewswire", "accesswire"}
FILING_DOMAINS = {"sec.gov", "edgar", "regulatory", "filing"}


def _origin_diversity_score(origins: List[SourceOriginRecord]) -> float:
    if not origins:
        return 0.0
    independent = sum(1 for o in origins if o.is_independent)
    return round(independent / len(origins), 2)


def _source_types(sources: List[SourceRecord]) -> List[str]:
    types: Set[str] = set()
    for s in sources:
        pub = s.publisher.lower()
        url = s.url.lower()
        if any(k in pub or k in url for k in PRESS_RELEASE_DOMAINS):
            types.add("press_release")
        elif any(k in pub or k in url for k in FILING_DOMAINS):
            types.add("filing")
        else:
            types.add("news")
    return sorted(list(types))


def _detect_gaps_deterministic(
    context: ResearchContext,
    claims: List[ExtractedClaim],
    events: List[ExtractedEvent],
) -> List[str]:
    """Identify research questions that lack matching evidence in extracted claims or events."""
    if not context.research_questions:
        return []

    claims_text = " ".join(c.text.lower() for c in claims)
    events_text = " ".join((e.title + " " + e.description).lower() for e in events)
    all_corpus = f"{claims_text} {events_text}"

    gaps: List[str] = []
    stop_words = {"what", "is", "the", "are", "their", "in", "of", "and", "to", "a", "for", "on", "how"}

    for question in context.research_questions:
        # Extract meaningful query keywords
        tokens = [w.lower().strip("?,.") for w in question.split() if w.lower().strip("?,.") not in stop_words]
        if not tokens:
            continue
        # If less than half of distinctive question tokens appear in findings, flag as gap
        matched = sum(1 for t in tokens if t in all_corpus)
        if matched < max(1, len(tokens) // 2):
            gaps.append(f"Insufficient source evidence retrieved for question: '{question}'")

    return gaps


def build_report(
    plan: ResearchPlan,
    executed: int,
    failed: int,
    sources: List[SourceRecord],
    origins: List[SourceOriginRecord],
    context: ResearchContext,
    claims: Optional[List[ExtractedClaim]] = None,
    events: Optional[List[ExtractedEvent]] = None,
    llm: Optional[LLMProvider] = None,
) -> CoverageReport:
    """Build research coverage report deterministically."""
    warnings: List[str] = []

    if not sources:
        warnings.append("No sources retrieved — search scope may be too narrow.")
    if failed > 0:
        warnings.append(f"{failed} of {len(plan.queries)} planned searches failed.")

    independent_origins = [o for o in origins if o.is_independent]
    if origins and len(independent_origins) <= 1:
        warnings.append(
            "All sources originate from a single editorial origin — treat as 1 independent confirmation."
        )

    gaps = _detect_gaps_deterministic(context, claims or [], events or [])

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
