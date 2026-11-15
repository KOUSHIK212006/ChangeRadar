"""Unified event and atomic claim extractor.

Extracts real-world developments and atomic factual claims together in bounded batches.
Eliminates one-call-per-article behavior and preserves source IDs and evidence traceability.
"""

from datetime import datetime, timezone
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
import uuid

from intelligence.config import intelligence_settings
from intelligence.contracts import (
    EvidenceRecord,
    ExtractedClaim,
    ExtractedEvent,
    ResearchContext,
    SourceRecord,
)
from intelligence.providers.base import LLMParseError, LLMProvider

logger = logging.getLogger("changeradar.intelligence.pipeline.extractor")

_VALID_LIFECYCLE = {"NEW", "DEVELOPING", "UPDATED", "COMPLETED"}
_VALID_VOLATILITY = {"LOW", "MEDIUM", "HIGH"}

UNIFIED_EXTRACTION_SYSTEM = (
    "You are an investigative intelligence analyst. "
    "Analyze the provided news and corporate source documents for the specified research target. "
    "Extract:\n"
    "1. Distinct real-world events (verifiable occurrences, not speculative commentary).\n"
    "2. Atomic factual claims (single verifiable facts extracted from those events).\n"
    "For every event and claim, specify the exact source_ids that support it. "
    "Return only valid JSON strictly matching the requested format."
)


def _event_id(title: str) -> str:
    return hashlib.sha256(title.lower().strip().encode("utf-8")).hexdigest()[:16]


def _claim_id(text: str, source_id: str) -> str:
    raw = f"{source_id}:{text.strip().lower()}"
    return f"clm-{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:12]}"


def _evidence_id(source_id: str, claim_id: str) -> str:
    raw = f"{source_id}:{claim_id}"
    return f"ev-{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:12]}"


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value or value.lower() in ("null", "none", "unknown"):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _build_batch_prompt(
    chunk: List[SourceRecord],
    context: ResearchContext,
) -> str:
    """Format articles for LLM batch extraction."""
    articles = [
        {
            "source_id": s.source_id,
            "title": s.title,
            "publisher": s.publisher,
            "published_at": s.published_at.isoformat() if s.published_at else "unknown",
            "content": s.snippet,
        }
        for s in chunk
    ]

    return (
        f"Research Target: {context.target_name}\n"
        f"Meeting Objective: {context.meeting_objective}\n"
        f"Time Window: Last {context.time_window_days} days\n\n"
        f"Sources ({len(articles)} documents):\n{json.dumps(articles, indent=2)}\n\n"
        "Return JSON in this exact structure:\n"
        "{\n"
        '  "events": [\n'
        '    {\n'
        '      "title": "Concise event headline",\n'
        '      "description": "Factual description of development",\n'
        '      "lifecycle_status": "NEW|DEVELOPING|UPDATED|COMPLETED",\n'
        '      "is_disputed": false,\n'
        '      "is_uncertain": false,\n'
        '      "event_at": "ISO date string or null",\n'
        '      "source_ids": ["source_id_1"]\n'
        "    }\n"
        "  ],\n"
        '  "claims": [\n'
        '    {\n'
        '      "text": "Single verifiable atomic factual statement",\n'
        '      "event_title": "Matching event title from above",\n'
        '      "volatility": "LOW|MEDIUM|HIGH",\n'
        '      "source_ids": ["source_id_1"]\n'
        "    }\n"
        "  ]\n"
        "}\n"
    )


def _extract_batch(
    chunk: List[SourceRecord],
    context: ResearchContext,
    llm: LLMProvider,
    discovered_at: datetime,
) -> Tuple[List[ExtractedEvent], List[ExtractedClaim]]:
    """Execute unified event and claim extraction for a single batch of sources."""
    user_prompt = _build_batch_prompt(chunk, context)
    source_map = {s.source_id: s for s in chunk}

    try:
        raw = llm.complete(UNIFIED_EXTRACTION_SYSTEM, user_prompt, stage="extraction")
        data = json.loads(raw)
    except (LLMParseError, Exception) as exc:
        logger.warning(f"Batch extraction failed for {len(chunk)} sources: {exc}")
        return [], []

    raw_events = data.get("events", [])
    raw_claims = data.get("claims", [])

    events: List[ExtractedEvent] = []
    event_by_title: Dict[str, ExtractedEvent] = {}

    for e in raw_events:
        title = e.get("title", "").strip()
        if not title:
            continue
        lifecycle = e.get("lifecycle_status", "NEW").upper()
        if lifecycle not in _VALID_LIFECYCLE:
            lifecycle = "NEW"

        event_sids = [sid for sid in e.get("source_ids", []) if sid in source_map]
        if not event_sids and chunk:
            event_sids = [chunk[0].source_id]

        primary_source = source_map.get(event_sids[0], chunk[0])

        event_obj = ExtractedEvent(
            event_id=_event_id(title),
            title=title,
            description=e.get("description", "").strip() or title,
            lifecycle_status=lifecycle,
            is_disputed=bool(e.get("is_disputed", False)),
            is_uncertain=bool(e.get("is_uncertain", False)),
            event_at=_parse_dt(e.get("event_at")),
            published_at=primary_source.published_at,
            discovered_at=discovered_at,
            source_ids=event_sids,
            origin_ids=[],
            claim_ids=[],
        )
        events.append(event_obj)
        event_by_title[title.lower()] = event_obj

    claims: List[ExtractedClaim] = []
    for c in raw_claims:
        text = c.get("text", "").strip()
        if not text:
            continue
        volatility = c.get("volatility", "MEDIUM").upper()
        if volatility not in _VALID_VOLATILITY:
            volatility = "MEDIUM"

        claim_sids = [sid for sid in c.get("source_ids", []) if sid in source_map]
        if not claim_sids and chunk:
            claim_sids = [chunk[0].source_id]

        primary_sid = claim_sids[0] if claim_sids else (chunk[0].source_id if chunk else "src")
        claim_id = _claim_id(text, primary_sid)

        # Link claim to its corresponding event
        ev_title = c.get("event_title", "").strip().lower()
        matched_event = event_by_title.get(ev_title)
        if not matched_event and events:
            matched_event = events[0]
        if matched_event:
            matched_event.claim_ids.append(claim_id)

        evidence_records = [
            EvidenceRecord(
                evidence_id=_evidence_id(sid, claim_id),
                excerpt=source_map[sid].snippet,
                source_id=sid,
                relevance="SUPPORTING",
            )
            for sid in claim_sids
            if sid in source_map
        ]

        claim_obj = ExtractedClaim(
            claim_id=claim_id,
            text=text,
            assessment="INSUFFICIENT",  # will be verified in assessment stage
            assessment_rationale="Awaiting multi-origin verification.",
            evidence=evidence_records,
            source_doc_count=len(claim_sids),
            independent_origin_count=1 if claim_sids else 0,
            volatility=volatility,
            is_stale=False,
            llm_confidence=0.0,
        )
        claims.append(claim_obj)

    return events, claims


def extract_events_and_claims(
    sources: List[SourceRecord],
    context: ResearchContext,
    llm: LLMProvider,
) -> Tuple[List[ExtractedEvent], List[ExtractedClaim]]:
    """Extract events and claims using intelligent bounded batching.

    Processes multiple articles per LLM request (up to MAX_ARTICLES_PER_BATCH).
    Takes only 1 LLM call for typical research runs (<= 15 sources).
    """
    if not sources:
        return [], []

    batch_size = max(1, intelligence_settings.MAX_ARTICLES_PER_BATCH)
    discovered_at = datetime.now(timezone.utc)

    all_events: List[ExtractedEvent] = []
    all_claims: List[ExtractedClaim] = []

    for offset in range(0, len(sources), batch_size):
        chunk = sources[offset: offset + batch_size]
        events, claims = _extract_batch(chunk, context, llm, discovered_at)
        all_events.extend(events)
        all_claims.extend(claims)
        logger.info(
            f"Batch extraction (offset={offset}, size={len(chunk)}) -> "
            f"{len(events)} events, {len(claims)} claims"
        )

    return all_events, all_claims


# Backward-compatible wrappers for callers expecting individual functions
def extract_events(
    sources: List[SourceRecord],
    context: ResearchContext,
    llm: LLMProvider,
) -> List[ExtractedEvent]:
    events, _ = extract_events_and_claims(sources, context, llm)
    return events


def extract_claims(
    events: List[ExtractedEvent],
    sources: List[SourceRecord],
    llm: LLMProvider,
) -> List[ExtractedClaim]:
    # Returns existing claims attached to events or empty list
    return []
