"""Source normalizer — deterministic deduplication, syndication detection, and origin grouping.

Rules (Stage B & D):
- NO LLM calls for URL normalization, date parsing, metadata extraction, or exact duplicate detection.
- Deterministic origin clustering using URL, title, publisher, and content similarity.
- Distinguishes independent investigative outlets from syndicated wire copies.
- Preserves source IDs, publisher metadata, URLs, and timestamps.
"""

from datetime import datetime
import hashlib
import re
from typing import List, Set, Tuple
from urllib.parse import urlparse

from intelligence.contracts import SourceOriginRecord, SourceRecord
from intelligence.providers.base import LLMProvider

PRESS_RELEASE_DOMAINS = {
    "businesswire.com",
    "prnewswire.com",
    "globenewswire.com",
    "accesswire.com",
    "prweb.com",
    "marketwire.com",
}


def _origin_id(label: str) -> str:
    """Stable SHA-256 origin identifier."""
    return hashlib.sha256(label.strip().lower().encode("utf-8")).hexdigest()[:16]


def _clean_title(title: str) -> str:
    """Normalize title for text similarity comparison."""
    # Remove publisher suffixes (e.g., " | Reuters", " - Bloomberg", " — BusinessWire")
    cleaned = re.sub(r"\s*[-|—–]\s*[A-Za-z0-9\s.]+$", "", title)
    # Remove non-alphanumeric characters
    cleaned = re.sub(r"[^\w\s]", "", cleaned.lower())
    return " ".join(cleaned.split())


def _title_similarity(t1: str, t2: str) -> float:
    """Jaccard similarity on word tokens."""
    words1 = set(_clean_title(t1).split())
    words2 = set(_clean_title(t2).split())
    if not words1 or not words2:
        return 0.0
    intersection = len(words1 & words2)
    union = len(words1 | words2)
    return intersection / union


def _get_domain(url: str) -> str:
    """Extract registered domain from URL."""
    try:
        netloc = urlparse(url).netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc
    except Exception:
        return ""


def _deduplicate(sources: List[SourceRecord]) -> List[SourceRecord]:
    """Deduplicate sources strictly by canonical_url."""
    seen: Set[str] = set()
    unique: List[SourceRecord] = []
    for s in sources:
        canon = s.canonical_url.strip().rstrip("/")
        if canon not in seen:
            seen.add(canon)
            unique.append(s)
    return unique


def _detect_syndication_and_origins(
    sources: List[SourceRecord],
) -> Tuple[List[SourceRecord], List[SourceOriginRecord]]:
    """Deterministically cluster sources into origin groups and identify syndicated republications."""
    if not sources:
        return [], []

    # Identify PR wires
    pr_wire_sources: List[SourceRecord] = []
    other_sources: List[SourceRecord] = []

    for s in sources:
        domain = _get_domain(s.url)
        is_pr_domain = any(prd in domain for prd in PRESS_RELEASE_DOMAINS)
        is_pr_title = "press release" in s.title.lower() or "official release" in s.title.lower()
        if is_pr_domain or is_pr_title:
            pr_wire_sources.append(s)
        else:
            other_sources.append(s)

    syndicated_ids: Set[str] = set()
    origins: List[SourceOriginRecord] = []
    assigned_source_ids: Set[str] = set()

    # 1. Group Press Release Wires by title similarity
    used_pr_indices: Set[int] = set()
    for i, pr1 in enumerate(pr_wire_sources):
        if i in used_pr_indices:
            continue
        cluster = [pr1]
        used_pr_indices.add(i)

        for j in range(i + 1, len(pr_wire_sources)):
            if j not in used_pr_indices:
                pr2 = pr_wire_sources[j]
                if _title_similarity(pr1.title, pr2.title) >= 0.5:
                    cluster.append(pr2)
                    used_pr_indices.add(j)

        # Also check if any general news outlets republished this press release verbatim
        for other in other_sources:
            if other.source_id not in assigned_source_ids:
                sim = _title_similarity(pr1.title, other.title)
                # If high title similarity to PR wire, mark as syndicated copy
                if sim >= 0.75:
                    cluster.append(other)
                    syndicated_ids.add(other.source_id)
                    assigned_source_ids.add(other.source_id)

        cluster_sids = [s.source_id for s in cluster]
        for sid in cluster_sids[1:]:
            syndicated_ids.add(sid)
        assigned_source_ids.update(cluster_sids)

        origins.append(
            SourceOriginRecord(
                origin_id=_origin_id(f"PR Wire: {pr1.title[:50]}"),
                label=f"Corporate Press Release / PR Wire ({cluster[0].publisher})",
                source_ids=cluster_sids,
                is_independent=False,
                independence_confidence=0.90,
            )
        )

    # 2. Group remaining independent media by publisher and story similarity
    remaining = [s for s in sources if s.source_id not in assigned_source_ids]
    publisher_map: dict[str, List[SourceRecord]] = {}

    for s in remaining:
        pub = s.publisher.strip() or _get_domain(s.url) or "Independent Source"
        publisher_map.setdefault(pub, []).append(s)

    for pub, pub_sources in publisher_map.items():
        origins.append(
            SourceOriginRecord(
                origin_id=_origin_id(pub),
                label=f"{pub} (Independent reporting)",
                source_ids=[s.source_id for s in pub_sources],
                is_independent=True,
                independence_confidence=0.85,
            )
        )

    # Update SourceRecord models with syndication flags
    updated_sources: List[SourceRecord] = []
    for s in sources:
        if s.source_id in syndicated_ids:
            updated_sources.append(
                s.model_copy(
                    update={
                        "is_syndicated": True,
                        "syndication_confidence": 0.90,
                    }
                )
            )
        else:
            updated_sources.append(s)

    return updated_sources, origins


def normalize(
    sources: List[SourceRecord],
    llm: LLMProvider,
) -> Tuple[List[SourceRecord], List[SourceOriginRecord]]:
    """Deduplicate, detect syndication, and group sources into origin clusters.

    Operates deterministically without wasting LLM quota.
    """
    unique_sources = _deduplicate(sources)
    return _detect_syndication_and_origins(unique_sources)
