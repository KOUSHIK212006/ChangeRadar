"""Delta computation — compares current results against the user's last reviewed baseline.

Returns None when no baseline is supplied (first run).
Generates EventVersionRecords for events that have materially changed.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from intelligence.contracts import (
    BaselineClaimSnapshot,
    BaselineEventSnapshot,
    DeltaRecord,
    EngineResultStatus,
    EventVersionRecord,
    IntelligenceResult,
    ResearchBaseline,
)
from intelligence.providers.base import LLMParseError, LLMProvider

logger = logging.getLogger("changeradar.intelligence.pipeline.delta")

UPDATE_SYSTEM = (
    "You are a change analyst. Determine whether an event description has changed materially "
    "from a baseline version. A material change is a meaningful new development, not just "
    "rephrasing. Return only valid JSON."
)


def _generate_event_versions(
    current: IntelligenceResult,
    event_snapshots: list[BaselineEventSnapshot],
    llm: LLMProvider,
) -> tuple[list[str], list[EventVersionRecord]]:
    """Compare ALL overlapping events against baseline in a single batched LLM call."""
    snapshot_map = {s.event_id: s for s in event_snapshots}
    now = datetime.now(timezone.utc)

    # Status changes are always material — no LLM needed
    trivial_updates: list[tuple[str, str]] = []  # (event_id, change_summary)
    needs_llm: list[tuple[str, str, str]] = []   # (event_id, old_desc, new_desc)

    for event in current.events:
        snapshot = snapshot_map.get(event.event_id)
        if not snapshot:
            continue
        if snapshot.lifecycle_status != event.lifecycle_status:
            trivial_updates.append((
                event.event_id,
                f"Lifecycle status changed from {snapshot.lifecycle_status} to {event.lifecycle_status}.",
            ))
        elif snapshot.description.strip() != event.description.strip():
            needs_llm.append((event.event_id, snapshot.description, event.description))

    # Batch LLM call for description-only changes
    llm_results: dict[str, tuple[bool, str]] = {}
    if needs_llm:
        items = [
            {
                "event_index": i,
                "event_id": eid,
                "baseline": old,
                "current": new,
            }
            for i, (eid, old, new) in enumerate(needs_llm)
        ]
        user_prompt = (
            f"Event comparisons:\n{json.dumps(items, indent=2)}\n\n"
            'Return JSON: {"changes": [{"event_index": 0, "is_material_change": true, "change_summary": "..."}]}\n'
            "Only mark as material if there is genuinely new information, not just rephrasing."
        )
        try:
            raw = llm.complete(UPDATE_SYSTEM, user_prompt)
            data = json.loads(raw)
            for c in data.get("changes", []):
                idx = c.get("event_index")
                if idx is not None and 0 <= idx < len(needs_llm):
                    eid = needs_llm[idx][0]
                    llm_results[eid] = (
                        bool(c.get("is_material_change", False)),
                        c.get("change_summary", ""),
                    )
        except (LLMParseError, Exception) as exc:
            logger.warning(f"Batched material change check failed: {exc}")

    updated_event_ids: list[str] = []
    versions: list[EventVersionRecord] = []

    for event_id, change_summary in trivial_updates:
        updated_event_ids.append(event_id)
        event = next(e for e in current.events if e.event_id == event_id)
        versions.append(EventVersionRecord(
            version_id=f"ver-{uuid.uuid4().hex[:8]}",
            event_id=event_id,
            description=event.description,
            changed_at=now,
            change_summary=change_summary,
        ))

    for event_id, _, _ in needs_llm:
        is_changed, change_summary = llm_results.get(event_id, (False, ""))
        if is_changed:
            updated_event_ids.append(event_id)
            event = next(e for e in current.events if e.event_id == event_id)
            versions.append(EventVersionRecord(
                version_id=f"ver-{uuid.uuid4().hex[:8]}",
                event_id=event_id,
                description=event.description,
                changed_at=now,
                change_summary=change_summary,
            ))

    return updated_event_ids, versions


def _detect_changed_assessments(
    current: IntelligenceResult,
    claim_snapshots: list[BaselineClaimSnapshot],
) -> list[str]:
    """Return claim_ids whose assessment status changed since baseline."""
    snapshot_map = {s.claim_id: s.assessment for s in claim_snapshots}
    changed: list[str] = []

    for claim in current.claims:
        old_assessment = snapshot_map.get(claim.claim_id)
        if old_assessment and old_assessment != claim.assessment:
            changed.append(claim.claim_id)

    return changed


def compute(
    current: IntelligenceResult,
    baseline: Optional[ResearchBaseline],
    llm: LLMProvider,
) -> tuple[Optional[DeltaRecord], list[EventVersionRecord]]:
    """Compute delta against baseline.

    Returns (DeltaRecord or None, list of new EventVersionRecords).
    """
    if baseline is None:
        return None, []

    is_partial = current.status == EngineResultStatus.PARTIAL

    current_event_ids = {e.event_id for e in current.events}
    current_claim_ids = {c.claim_id for c in current.claims}
    baseline_event_ids = set(baseline.known_event_ids)
    baseline_claim_ids = set(baseline.known_claim_ids)

    # New events — present now but not in baseline
    new_events = list(current_event_ids - baseline_event_ids)

    # Updated events — use LLM comparison against snapshots
    updated_events: list[str] = []
    event_versions: list[EventVersionRecord] = []
    if baseline.event_snapshots:
        updated_events, event_versions = _generate_event_versions(current, baseline.event_snapshots, llm)

    # New evidence for existing claims — claims present now but not in baseline
    new_evidence_for_claims = list(current_claim_ids - baseline_claim_ids)

    # Changed assessments — use snapshots for comparison
    changed_assessments: list[str] = []
    if baseline.claim_snapshots:
        changed_assessments = _detect_changed_assessments(current, baseline.claim_snapshots)

    no_material_change = (
        not new_events
        and not updated_events
        and not new_evidence_for_claims
        and not changed_assessments
        and not is_partial
    )

    delta = DeltaRecord(
        new_events=new_events,
        updated_events=updated_events,
        new_evidence_for_claims=new_evidence_for_claims,
        changed_assessments=changed_assessments,
        no_material_change=no_material_change,
        comparison_incomplete=is_partial,
        incompleteness_reason="Current run is PARTIAL — some sources may be missing." if is_partial else None,
    )

    return delta, event_versions
