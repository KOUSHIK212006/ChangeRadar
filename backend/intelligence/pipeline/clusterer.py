"""Event clusterer — deterministic duplicate event resolution.

Rules (Stage D):
- Merges duplicate events describing the same real-world development without LLM overhead.
- Uses token similarity, keyword overlap, and time window proximity.
- Preserves all source IDs, origin IDs, and claim references.
"""

from datetime import datetime
import hashlib
import logging
import re
from typing import List, Set

from intelligence.contracts import ExtractedEvent, SourceRecord
from intelligence.providers.base import LLMProvider

logger = logging.getLogger("changeradar.intelligence.pipeline.clusterer")


def _event_id(title: str) -> str:
    return hashlib.sha256(title.lower().strip().encode("utf-8")).hexdigest()[:16]


def _clean_text(text: str) -> str:
    cleaned = re.sub(r"[^\w\s]", "", text.lower())
    return " ".join(cleaned.split())


def _similarity(s1: str, s2: str) -> float:
    w1 = set(_clean_text(s1).split())
    w2 = set(_clean_text(s2).split())
    if not w1 or not w2:
        return 0.0
    return len(w1 & w2) / len(w1 | w2)


def _merge_cluster(group: List[ExtractedEvent]) -> ExtractedEvent:
    """Merge an event cluster into a single canonical event."""
    primary = max(group, key=lambda e: len(e.description))
    all_source_ids = sorted(list({sid for e in group for sid in e.source_ids}))
    all_origin_ids = sorted(list({oid for e in group for oid in e.origin_ids}))
    all_claim_ids = sorted(list({cid for e in group for cid in e.claim_ids}))

    event_ats = [e.event_at for e in group if e.event_at]
    published_ats = [e.published_at for e in group if e.published_at]

    return primary.model_copy(
        update={
            "event_id": _event_id(primary.title),
            "source_ids": all_source_ids,
            "origin_ids": all_origin_ids,
            "claim_ids": all_claim_ids,
            "event_at": min(event_ats) if event_ats else primary.event_at,
            "published_at": min(published_ats) if published_ats else primary.published_at,
            "is_disputed": any(e.is_disputed for e in group),
            "is_uncertain": any(e.is_uncertain for e in group),
        }
    )


def cluster_events(
    events: List[ExtractedEvent],
    sources: List[SourceRecord],
    llm: LLMProvider,
) -> List[ExtractedEvent]:
    """Cluster duplicate events deterministically using title & description similarity."""
    if len(events) <= 1:
        return events

    clusters: List[List[ExtractedEvent]] = []
    used_indices: Set[int] = set()

    for i in range(len(events)):
        if i in used_indices:
            continue
        cluster = [events[i]]
        used_indices.add(i)

        for j in range(i + 1, len(events)):
            if j not in used_indices:
                title_sim = _similarity(events[i].title, events[j].title)
                desc_sim = _similarity(events[i].description, events[j].description)
                # If high title similarity or strong description overlap, cluster them
                if title_sim >= 0.60 or desc_sim >= 0.70:
                    cluster.append(events[j])
                    used_indices.add(j)

        clusters.append(cluster)

    merged: List[ExtractedEvent] = []
    for c in clusters:
        merged.append(_merge_cluster(c) if len(c) > 1 else c[0])

    logger.debug(f"Event clustering: {len(events)} events merged into {len(merged)} clusters")
    return merged
