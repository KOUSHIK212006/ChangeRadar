"""Deterministic temporal analysis and delta computation against review baseline.

Rules (Stage F):
- 100% deterministic Python logic for baseline comparison and delta generation.
- No LLM calls for timestamp comparisons, state transitions, or text differences.
- Preserves review history and tracks material description updates.
- Distinguishes event date, publication date, and discovery time.
"""

from datetime import datetime, timezone
import difflib
import logging
from typing import List, Optional, Tuple
import uuid

from intelligence.contracts import (
    BaselineClaimSnapshot,
    BaselineEventSnapshot,
    DeltaRecord,
    EngineResultStatus,
    EventVersionRecord,
    IntelligenceResult,
    ResearchBaseline,
)
from intelligence.providers.base import LLMProvider

logger = logging.getLogger("changeradar.intelligence.pipeline.delta")


def _is_material_description_change(old_desc: str, new_desc: str) -> Tuple[bool, str]:
    """Deterministically check if description has materially changed using sequence matching."""
    s1 = old_desc.strip()
    s2 = new_desc.strip()
    if s1 == s2:
        return False, ""

    ratio = difflib.SequenceMatcher(None, s1, s2).ratio()
    if ratio < 0.85:
        # Significant content difference
        return True, "Material description update based on newly retrieved source details."
    return False, ""


def compute(
    current: IntelligenceResult,
    baseline: Optional[ResearchBaseline],
    llm: Optional[LLMProvider] = None,
) -> Tuple[Optional[DeltaRecord], List[EventVersionRecord]]:
    """Compute delta against user-reviewed baseline deterministically without LLM calls."""
    if baseline is None:
        return None, []

    is_partial = current.status == EngineResultStatus.PARTIAL
    now = datetime.now(timezone.utc)

    current_event_ids = {e.event_id for e in current.events}
    current_claim_ids = {c.claim_id for c in current.claims}
    baseline_event_ids = set(baseline.known_event_ids)
    baseline_claim_ids = set(baseline.known_claim_ids)

    # 1. New events: present now but absent from baseline
    new_events = sorted(list(current_event_ids - baseline_event_ids))

    # 2. Updated events & versions
    updated_events: List[str] = []
    event_versions: List[EventVersionRecord] = []

    # Map baseline snapshots if available
    event_snapshot_map: dict[str, BaselineEventSnapshot] = {
        s.event_id: s for s in getattr(baseline, "event_snapshots", [])
    }

    for ev in current.events:
        if ev.event_id in baseline_event_ids:
            snapshot = event_snapshot_map.get(ev.event_id)
            if snapshot:
                # Check status transition
                if snapshot.lifecycle_status != ev.lifecycle_status:
                    updated_events.append(ev.event_id)
                    event_versions.append(
                        EventVersionRecord(
                            version_id=f"ver-{uuid.uuid4().hex[:8]}",
                            event_id=ev.event_id,
                            description=ev.description,
                            changed_at=now,
                            change_summary=f"Lifecycle transition: {snapshot.lifecycle_status} -> {ev.lifecycle_status}.",
                        )
                    )
                else:
                    # Check description diff
                    changed, summary = _is_material_description_change(
                        snapshot.description, ev.description
                    )
                    if changed:
                        updated_events.append(ev.event_id)
                        event_versions.append(
                            EventVersionRecord(
                                version_id=f"ver-{uuid.uuid4().hex[:8]}",
                                event_id=ev.event_id,
                                description=ev.description,
                                changed_at=now,
                                change_summary=summary,
                            )
                        )

    # 3. New evidence for claims
    new_evidence_for_claims = sorted(list(current_claim_ids - baseline_claim_ids))

    # 4. Changed assessments
    changed_assessments: List[str] = []
    claim_snapshot_map: dict[str, str] = {
        s.claim_id: s.assessment for s in getattr(baseline, "claim_snapshots", [])
    }

    for c in current.claims:
        old_assessment = claim_snapshot_map.get(c.claim_id)
        if old_assessment and old_assessment != c.assessment:
            changed_assessments.append(c.claim_id)

    no_material_change = (
        not new_events
        and not updated_events
        and not new_evidence_for_claims
        and not changed_assessments
        and not is_partial
    )

    delta = DeltaRecord(
        new_events=new_events,
        updated_events=sorted(list(set(updated_events))),
        new_evidence_for_claims=new_evidence_for_claims,
        changed_assessments=sorted(changed_assessments),
        no_material_change=no_material_change,
        comparison_incomplete=is_partial,
        incompleteness_reason="Current run is PARTIAL — comparison may be incomplete." if is_partial else None,
    )

    logger.debug(
        f"Delta computed: new_events={len(new_events)}, updated={len(updated_events)}, "
        f"new_evidence={len(new_evidence_for_claims)}, changed_assessments={len(changed_assessments)}"
    )

    return delta, event_versions
