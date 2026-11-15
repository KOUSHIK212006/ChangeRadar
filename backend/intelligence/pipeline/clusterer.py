"""Event clusterer — merges duplicate events describing the same real-world development.

Uses LLM to identify which extracted events are the same development,
then merges them: keeps the most detailed description, unions source_ids and origin_ids.
"""

import hashlib
import json
import logging

from intelligence.contracts import ExtractedEvent, SourceRecord
from intelligence.providers.base import LLMParseError, LLMProvider

logger = logging.getLogger("changeradar.intelligence.pipeline.clusterer")


def _event_id(title: str) -> str:
    return hashlib.sha256(title.lower().strip().encode()).hexdigest()[:16]


def _merge_cluster(group: list[ExtractedEvent]) -> ExtractedEvent:
    """Merge a cluster into one event — keep longest description, union sources."""
    primary = max(group, key=lambda e: len(e.description))
    all_source_ids = list({sid for e in group for sid in e.source_ids})
    all_origin_ids = list({oid for e in group for oid in e.origin_ids})
    all_claim_ids = list({cid for e in group for cid in e.claim_ids})

    # Use earliest event_at and published_at across the cluster
    event_ats = [e.event_at for e in group if e.event_at]
    published_ats = [e.published_at for e in group if e.published_at]

    return primary.model_copy(update={
        "event_id": _event_id(primary.title),
        "source_ids": all_source_ids,
        "origin_ids": all_origin_ids,
        "claim_ids": all_claim_ids,
        "event_at": min(event_ats) if event_ats else primary.event_at,
        "published_at": min(published_ats) if published_ats else primary.published_at,
        "is_disputed": any(e.is_disputed for e in group),
        "is_uncertain": any(e.is_uncertain for e in group),
    })


def cluster_events(
    events: list[ExtractedEvent],
    sources: list[SourceRecord],
    llm: LLMProvider,
) -> list[ExtractedEvent]:
    """Identify duplicate events and merge them into single canonical events."""
    if len(events) <= 1:
        return events

    items = [{"index": i, "title": e.title, "description": e.description[:300]} for i, e in enumerate(events)]
    system = (
        "You are an event analyst. Identify which extracted events describe the same "
        "real-world development. Be conservative — only cluster when clearly the same event. "
        "Return only valid JSON."
    )
    user = (
        f"Events:\n{json.dumps(items, indent=2)}\n\n"
        'Return JSON: {"clusters": [[0, 2], [1], [3, 4]]}\n'
        "Each inner list contains event indexes that are the same development. "
        "Every index must appear in exactly one cluster."
    )

    try:
        raw = llm.complete(system, user)
        data = json.loads(raw)
        clusters: list[list[int]] = data.get("clusters", [])
    except (LLMParseError, Exception) as exc:
        logger.warning(f"Event clustering LLM call failed, returning events as-is: {exc}")
        return events

    # Validate all indexes are present
    all_indexes = {i for cluster in clusters for i in cluster}
    missing = set(range(len(events))) - all_indexes
    for idx in missing:
        clusters.append([idx])

    merged: list[ExtractedEvent] = []
    for cluster in clusters:
        valid = [events[i] for i in cluster if 0 <= i < len(events)]
        if not valid:
            continue
        merged.append(_merge_cluster(valid) if len(valid) > 1 else valid[0])

    return merged
