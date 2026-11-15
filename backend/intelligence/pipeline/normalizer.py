"""Source normalizer — deduplication, syndication detection, and origin grouping.

Steps:
1. Deduplicate by canonical_url — keep first occurrence.
2. Detect syndicated sources via LLM batch call.
3. Group sources into origin clusters via LLM.
"""

import hashlib
import json
import logging
import time

from intelligence.contracts import SourceOriginRecord, SourceRecord
from intelligence.providers.base import LLMParseError, LLMProvider

logger = logging.getLogger("changeradar.intelligence.pipeline.normalizer")

_SYNDICATION_CHUNK = 20   # max sources per syndication LLM call
_ORIGIN_CHUNK = 20        # max sources per origin grouping LLM call
_INTER_CALL_SLEEP = 2     # seconds between consecutive LLM calls to avoid 429


def _origin_id(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()[:16]


def _deduplicate(sources: list[SourceRecord]) -> list[SourceRecord]:
    seen: set[str] = set()
    unique: list[SourceRecord] = []
    for s in sources:
        if s.canonical_url not in seen:
            seen.add(s.canonical_url)
            unique.append(s)
    return unique


def _detect_syndication(sources: list[SourceRecord], llm: LLMProvider) -> list[SourceRecord]:
    if len(sources) < 2:
        return sources

    syndicated_ids: dict[str, float] = {}

    for offset in range(0, len(sources), _SYNDICATION_CHUNK):
        chunk = sources[offset: offset + _SYNDICATION_CHUNK]
        items = [{"source_id": s.source_id, "title": s.title, "snippet": s.snippet[:200]} for s in chunk]
        system = (
            "You are a source analyst. Identify which news articles appear to be republications "
            "of the same original story (syndicated content). Be conservative — only group when "
            "the content is clearly the same story. Return only valid JSON."
        )
        user = (
            f"Articles:\n{json.dumps(items, indent=2)}\n\n"
            'Return JSON: {"syndication_groups": [["source_id", "source_id"], ...]}\n'
            "Each inner list is a group of source_ids that are the same story. "
            "Singletons are not needed. Return empty list if nothing is clearly syndicated."
        )
        try:
            raw = llm.complete(system, user)
            data = json.loads(raw)
            for group in data.get("syndication_groups", []):
                if len(group) > 1:
                    for sid in group[1:]:
                        syndicated_ids[sid] = 0.9
        except (LLMParseError, Exception) as exc:
            logger.warning(f"Syndication detection chunk (offset={offset}) failed: {exc}")

        if offset + _SYNDICATION_CHUNK < len(sources):
            time.sleep(_INTER_CALL_SLEEP)

    updated: list[SourceRecord] = []
    for s in sources:
        if s.source_id in syndicated_ids:
            updated.append(s.model_copy(update={
                "is_syndicated": True,
                "syndication_confidence": syndicated_ids[s.source_id],
            }))
        else:
            updated.append(s)
    return updated


def _group_origins(sources: list[SourceRecord], llm: LLMProvider) -> list[SourceOriginRecord]:
    if not sources:
        return []

    all_source_ids = {s.source_id for s in sources}
    assigned: set[str] = set()
    origins: list[SourceOriginRecord] = []

    time.sleep(_INTER_CALL_SLEEP)  # avoid 429 after syndication calls

    for offset in range(0, len(sources), _ORIGIN_CHUNK):
        chunk = sources[offset: offset + _ORIGIN_CHUNK]
        items = [{"source_id": s.source_id, "publisher": s.publisher, "title": s.title} for s in chunk]
        system = (
            "You are a source analyst. Group news sources by their likely original information origin. "
            "For example, multiple outlets republishing one press release = one origin. "
            "An independent investigative report = its own origin. Be conservative. "
            "Return only valid JSON."
        )
        user = (
            f"Sources:\n{json.dumps(items, indent=2)}\n\n"
            'Return JSON: {"origin_groups": [{"label": "...", "source_ids": [...], '
            '"is_independent": true, "confidence": 0.0}]}\n'
            "Every source_id must appear in exactly one group."
        )
        try:
            raw = llm.complete(system, user)
            data = json.loads(raw)
            for g in data.get("origin_groups", []):
                label = g.get("label", "Unknown Origin")
                source_ids = [sid for sid in g.get("source_ids", []) if sid in all_source_ids]
                if not source_ids:
                    continue
                assigned.update(source_ids)
                origins.append(SourceOriginRecord(
                    origin_id=_origin_id(label),
                    label=label,
                    source_ids=source_ids,
                    is_independent=bool(g.get("is_independent", True)),
                    independence_confidence=float(g.get("confidence", 0.5)),
                ))
        except (LLMParseError, Exception) as exc:
            logger.warning(f"Origin grouping chunk (offset={offset}) failed: {exc}")

        if offset + _ORIGIN_CHUNK < len(sources):
            time.sleep(_INTER_CALL_SLEEP)

    # Any source not assigned by LLM gets its own fallback origin
    for s in sources:
        if s.source_id not in assigned:
            origins.append(SourceOriginRecord(
                origin_id=_origin_id(s.publisher),
                label=s.publisher,
                source_ids=[s.source_id],
                is_independent=True,
                independence_confidence=0.5,
            ))

    return origins



def normalize(
    sources: list[SourceRecord],
    llm: LLMProvider,
) -> tuple[list[SourceRecord], list[SourceOriginRecord]]:
    """Deduplicate, detect syndication, and group sources into origins."""
    sources = _deduplicate(sources)
    sources = _detect_syndication(sources, llm)
    origins = _group_origins(sources, llm)
    return sources, origins
