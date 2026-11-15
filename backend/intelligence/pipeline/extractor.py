"""Event and claim extractor — chunked batches.

Sources are processed in chunks of CHUNK_SIZE to stay within LLM context limits.
Claims are extracted from all events in one call (events are small).
"""

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone

from intelligence.contracts import (
    ExtractedClaim,
    ExtractedEvent,
    ResearchContext,
    SourceRecord,
)
from intelligence.providers.base import LLMParseError, LLMProvider

logger = logging.getLogger("changeradar.intelligence.pipeline.extractor")

_VALID_LIFECYCLE = {"NEW", "DEVELOPING", "UPDATED", "COMPLETED"}
_VALID_VOLATILITY = {"LOW", "MEDIUM", "HIGH"}
_CHUNK_SIZE = 10  # max sources per LLM call to stay within context limits

EVENT_SYSTEM = (
    "You are an intelligence analyst. Given a list of news articles, extract distinct "
    "real-world events from ALL of them. An event is a specific development that happened — "
    "not an opinion or prediction. Each event must include the source_index it came from. "
    "Return only valid JSON."
)

CLAIM_SYSTEM = (
    "You are a fact extractor. Given a list of events, extract atomic factual claims from "
    "ALL of them. Each claim must be a single, specific, verifiable statement — no opinions "
    "or predictions. Each claim must include the event_index it came from. "
    "Return only valid JSON."
)


def _event_id(title: str) -> str:
    return hashlib.sha256(title.lower().strip().encode()).hexdigest()[:16]


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _extract_events_chunk(
    chunk: list[SourceRecord],
    chunk_offset: int,
    context: ResearchContext,
    llm: LLMProvider,
    discovered_at: datetime,
) -> list[ExtractedEvent]:
    """Extract events from a single chunk of sources."""
    articles = [
        {
            "source_index": chunk_offset + i,
            "source_id": s.source_id,
            "title": s.title,
            "publisher": s.publisher,
            "published": s.published_at.isoformat() if s.published_at else "unknown",
            "content": s.snippet[:300],
        }
        for i, s in enumerate(chunk)
    ]

    user_prompt = (
        f"Research target: {context.target_name}\n"
        f"Meeting objective: {context.meeting_objective}\n\n"
        f"Articles:\n{json.dumps(articles, indent=2)}\n\n"
        'Return JSON: {"events": [{"source_index": 0, "title": "...", "description": "...", '
        '"event_at": "ISO date or null", "lifecycle_status": "NEW|DEVELOPING|UPDATED|COMPLETED", '
        '"is_disputed": false, "is_uncertain": false}]}'
    )

    try:
        raw = llm.complete(EVENT_SYSTEM, user_prompt)
        data = json.loads(raw)
        raw_events = data.get("events", [])
    except (LLMParseError, Exception) as exc:
        logger.warning(f"Event extraction chunk (offset={chunk_offset}) failed: {exc}")
        return []

    events: list[ExtractedEvent] = []
    # Build a flat index across all sources for source_index lookup
    all_sources_in_chunk = {chunk_offset + i: s for i, s in enumerate(chunk)}

    for e in raw_events:
        title = e.get("title", "").strip()
        if not title:
            continue
        lifecycle = e.get("lifecycle_status", "NEW").upper()
        if lifecycle not in _VALID_LIFECYCLE:
            lifecycle = "NEW"

        src_idx = e.get("source_index", chunk_offset)
        source = all_sources_in_chunk.get(src_idx, chunk[0])

        events.append(ExtractedEvent(
            event_id=_event_id(title),
            title=title,
            description=e.get("description", ""),
            lifecycle_status=lifecycle,
            is_disputed=bool(e.get("is_disputed", False)),
            is_uncertain=bool(e.get("is_uncertain", False)),
            event_at=_parse_dt(e.get("event_at")),
            published_at=source.published_at,
            discovered_at=discovered_at,
            source_ids=[source.source_id],
            origin_ids=[],
            claim_ids=[],
        ))

    return events


def extract_events(
    sources: list[SourceRecord],
    context: ResearchContext,
    llm: LLMProvider,
) -> list[ExtractedEvent]:
    """Extract events from sources in chunks to stay within LLM context limits."""
    if not sources:
        return []

    discovered_at = datetime.now(timezone.utc)
    all_events: list[ExtractedEvent] = []

    for offset in range(0, len(sources), _CHUNK_SIZE):
        chunk = sources[offset: offset + _CHUNK_SIZE]
        chunk_events = _extract_events_chunk(chunk, offset, context, llm, discovered_at)
        all_events.extend(chunk_events)
        logger.info(f"Extracted {len(chunk_events)} events from chunk offset={offset}")

    return all_events


def extract_claims(
    events: list[ExtractedEvent],
    sources: list[SourceRecord],
    llm: LLMProvider,
) -> list[ExtractedClaim]:
    """Extract atomic claims from ALL events in a single batched LLM call."""
    if not events:
        return []

    event_items = [
        {
            "event_index": i,
            "event_id": e.event_id,
            "title": e.title,
            "description": e.description,
        }
        for i, e in enumerate(events)
    ]

    user_prompt = (
        f"Events:\n{json.dumps(event_items, indent=2)}\n\n"
        'Return JSON: {"claims": [{"event_index": 0, "text": "...", "volatility": "LOW|MEDIUM|HIGH"}]}\n'
        "Each claim must be a single verifiable fact. No opinions or predictions."
    )

    try:
        raw = llm.complete(CLAIM_SYSTEM, user_prompt)
        data = json.loads(raw)
        raw_claims = data.get("claims", [])
    except (LLMParseError, Exception) as exc:
        logger.warning(f"Batched claim extraction failed: {exc}")
        return []

    claims: list[ExtractedClaim] = []
    for c in raw_claims:
        text = c.get("text", "").strip()
        if not text:
            continue
        volatility = c.get("volatility", "MEDIUM").upper()
        if volatility not in _VALID_VOLATILITY:
            volatility = "MEDIUM"

        ev_idx = c.get("event_index", 0)
        event = events[ev_idx] if 0 <= ev_idx < len(events) else events[0]

        claim_id = f"clm-{uuid.uuid4().hex[:8]}"
        claims.append(ExtractedClaim(
            claim_id=claim_id,
            text=text,
            assessment="INSUFFICIENT",
            assessment_rationale="Pending assessment.",
            evidence=[],
            source_doc_count=len(event.source_ids),
            independent_origin_count=0,
            volatility=volatility,
            is_stale=False,
            llm_confidence=0.0,
        ))
        event.claim_ids.append(claim_id)

    return claims
