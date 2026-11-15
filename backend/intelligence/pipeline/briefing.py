"""Briefing generator — synthesized executive pre-meeting intelligence.

Rules (Stage G):
- Generates the final executive briefing using ONE structured LLM request.
- Reuses already extracted events and assessed claims.
- Never re-extracts or re-assesses facts; grounds all narrative in collected evidence.
- Highlights contradictions, uncertainties, and coverage limitations.
"""

import json
import logging
from typing import List, Optional

from intelligence.contracts import (
    CoverageReport,
    DeltaRecord,
    ExtractedClaim,
    ExtractedEvent,
    ResearchContext,
)
from intelligence.providers.base import LLMParseError, LLMProvider

logger = logging.getLogger("changeradar.intelligence.pipeline.briefing")

BRIEFING_SYSTEM = (
    "You are an executive intelligence analyst. "
    "Synthesize a clear, evidence-grounded briefing for the upcoming meeting based strictly on the provided developments and verified claims.\n"
    "Rules:\n"
    "- Ground all summary statements directly in the supplied events and claims.\n"
    "- Explicitly call out any contradictory evidence or unresolved uncertainties.\n"
    "- Note search coverage limitations.\n"
    "- Return only valid JSON."
)


def generate_briefing_summary(
    context: ResearchContext,
    events: List[ExtractedEvent],
    claims: List[ExtractedClaim],
    coverage: CoverageReport,
    delta: Optional[DeltaRecord],
    llm: LLMProvider,
) -> str:
    """Synthesize high-level briefing narrative in one structured LLM call."""
    if not events and not claims:
        return f"No verified developments or claims identified for {context.target_name} within the searched lookback period."

    events_summary = [{"title": e.title, "description": e.description[:200]} for e in events[:5]]
    claims_summary = [
        {"text": c.text, "assessment": c.assessment, "rationale": c.assessment_rationale}
        for c in claims[:8]
    ]

    user_prompt = (
        f"Research Target: {context.target_name}\n"
        f"Meeting Objective: {context.meeting_objective}\n\n"
        f"Key Events ({len(events_summary)}):\n{json.dumps(events_summary, indent=2)}\n\n"
        f"Verified Claims ({len(claims_summary)}):\n{json.dumps(claims_summary, indent=2)}\n\n"
        f"Coverage Gaps / Warnings:\n{json.dumps(coverage.gaps + coverage.warnings, indent=2)}\n\n"
        "Return JSON:\n"
        '{"executive_briefing": "Concise 2-3 paragraph synthesized intelligence briefing highlighting what changed, what matters, and key contradictory or unverified assertions to watch for."}'
    )

    try:
        raw = llm.complete(BRIEFING_SYSTEM, user_prompt, stage="briefing")
        data = json.loads(raw)
        return data.get("executive_briefing", "").strip() or _fallback_summary(context, events, claims)
    except (LLMParseError, Exception) as exc:
        logger.warning(f"Briefing generation LLM call failed: {exc}")
        return _fallback_summary(context, events, claims)


def _fallback_summary(
    context: ResearchContext,
    events: List[ExtractedEvent],
    claims: List[ExtractedClaim],
) -> str:
    """Deterministic fallback summary when briefing LLM call fails."""
    num_events = len(events)
    num_claims = len(claims)
    contradicted = [c for c in claims if c.assessment == "CONTRADICTED"]

    summary = f"Synthesized research briefing for {context.target_name}. Analyzed {num_events} developments and {num_claims} atomic claims."
    if contradicted:
        summary += f" Detected {len(contradicted)} directly contradicted statement(s) in source reporting."
    return summary

