"""Research planner — generates targeted search queries and entity aliases from context."""

import json
import logging

from pydantic import BaseModel

from intelligence.contracts import ResearchContext
from intelligence.providers.base import LLMParseError, LLMProvider

logger = logging.getLogger("changeradar.intelligence.pipeline.planner")

SYSTEM_PROMPT = (
    "You are a research planner. Given a target entity and meeting context, "
    "generate specific search queries and entity aliases. "
    "Return only valid JSON in the exact shape requested. "
    "Do not include generic queries. Focus on what would matter for the meeting objective."
)


class ResearchPlan(BaseModel):
    queries: list[str]          # 3–6 targeted search queries
    entity_aliases: list[str]   # alternate names / ticker symbols / abbreviations
    time_filter: str            # e.g. "past month"


def plan(context: ResearchContext, llm: LLMProvider) -> ResearchPlan:
    """Generate a research plan from the supplied context using the LLM provider."""
    questions_text = "\n".join(f"- {q}" for q in context.research_questions) or "None provided."

    user_prompt = (
        f"Target: {context.target_name}\n"
        f"Target type: {context.target_type or 'unknown'}\n"
        f"Meeting objective: {context.meeting_objective}\n"
        f"Time window: last {context.time_window_days} days\n"
        f"Research questions:\n{questions_text}\n\n"
        "Return JSON:\n"
        '{"queries": ["...", "..."], "entity_aliases": ["...", "..."], "time_filter": "..."}\n'
        "Generate 3 to 6 specific queries. Include at least one query covering recent news, "
        "one covering financials or performance, and one covering leadership or strategy."
    )

    try:
        raw = llm.complete(SYSTEM_PROMPT, user_prompt)
        data = json.loads(raw)
        return ResearchPlan.model_validate(data)
    except (LLMParseError, Exception) as exc:
        logger.warning(f"Planner LLM call failed, falling back to basic queries: {exc}")
        return _fallback_plan(context)


def _fallback_plan(context: ResearchContext) -> ResearchPlan:
    """Return a minimal deterministic plan when the LLM call fails."""
    name = context.target_name
    return ResearchPlan(
        queries=[
            f"{name} latest news",
            f"{name} financial results",
            f"{name} leadership strategy",
        ],
        entity_aliases=[name],
        time_filter=f"past {context.time_window_days} days",
    )
