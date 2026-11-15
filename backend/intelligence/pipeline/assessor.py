"""Claim assessor — batched.

1 LLM call for ALL claims at once.
Total: 1 call (was 1 per claim).
"""

import json
import logging
import uuid
from datetime import datetime, timezone

from intelligence.contracts import (
    EvidenceRecord,
    ExtractedClaim,
    SourceOriginRecord,
    SourceRecord,
)
from intelligence.providers.base import LLMParseError, LLMProvider

logger = logging.getLogger("changeradar.intelligence.pipeline.assessor")

_VALID_ASSESSMENTS = {
    "SUPPORTED", "PARTIALLY_SUPPORTED", "CONTRADICTED",
    "INSUFFICIENT", "OUTDATED", "UNVERIFIABLE",
}

ASSESS_SYSTEM = (
    "You are an evidence analyst. Assess each factual claim against the provided source excerpts. "
    "Use only the evidence given — do not invent facts. "
    "Return one assessment object per claim in the same order. "
    "Return only valid JSON."
)


def _find_relevant_sources(claim: ExtractedClaim, sources: list[SourceRecord]) -> list[SourceRecord]:
    claim_words = set(claim.text.lower().split())
    scored = []
    for s in sources:
        overlap = len(claim_words & set((s.title + " " + s.snippet).lower().split()))
        if overlap > 0:
            scored.append((overlap, s))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in scored[:5]]


def _count_independent_origins(source_ids: list[str], origins: list[SourceOriginRecord]) -> int:
    count = sum(
        1 for o in origins
        if o.is_independent and any(sid in o.source_ids for sid in source_ids)
    )
    return max(count, 1) if source_ids else 0


def _is_stale(claim: ExtractedClaim, sources: list[SourceRecord]) -> bool:
    if claim.volatility == "LOW":
        return False
    supporting = [s for s in sources if s.source_id in {e.source_id for e in claim.evidence}]
    if not supporting:
        return False
    newest = max((s.published_at for s in supporting if s.published_at), default=None)
    if newest is None:
        return False
    age_days = (datetime.now(timezone.utc) - newest).days
    if claim.volatility == "HIGH":
        return age_days > 7
    if claim.volatility == "MEDIUM":
        return age_days > 30
    return False


def assess_claims(
    claims: list[ExtractedClaim],
    sources: list[SourceRecord],
    origins: list[SourceOriginRecord],
    llm: LLMProvider,
) -> list[ExtractedClaim]:
    """Assess ALL claims in a single batched LLM call."""
    if not claims:
        return []

    # Build per-claim evidence lookup (no LLM needed — keyword overlap)
    claim_sources: list[list[SourceRecord]] = [
        _find_relevant_sources(c, sources) for c in claims
    ]

    # Mark claims with no sources immediately — skip from LLM batch
    no_source_indices = {i for i, cs in enumerate(claim_sources) if not cs}

    batch_items = []
    batch_index_map: list[int] = []  # maps batch position → original claim index
    for i, (claim, relevant) in enumerate(zip(claims, claim_sources)):
        if i in no_source_indices:
            continue
        batch_items.append({
            "claim_index": len(batch_index_map),
            "claim_id": claim.claim_id,
            "claim": claim.text,
            "evidence": [
                {
                    "source_id": s.source_id,
                    "excerpt": s.snippet[:300],
                    "publisher": s.publisher,
                    "published_at": s.published_at.isoformat() if s.published_at else "unknown",
                }
                for s in relevant
            ],
        })
        batch_index_map.append(i)

    # Default results for all claims
    results: dict[int, dict] = {}

    if batch_items:
        user_prompt = (
            f"Claims and evidence:\n{json.dumps(batch_items, indent=2)}\n\n"
            "Return JSON:\n"
            '{"assessments": [{"claim_index": 0, '
            '"assessment": "SUPPORTED|PARTIALLY_SUPPORTED|CONTRADICTED|INSUFFICIENT|OUTDATED|UNVERIFIABLE", '
            '"rationale": "one sentence", '
            '"supporting_source_ids": [], '
            '"contradicting_source_ids": [], '
            '"confidence": 0.0}]}\n\n'
            "Rules:\n"
            "- SUPPORTED: multiple independent sources confirm it\n"
            "- PARTIALLY_SUPPORTED: some evidence supports, some is missing\n"
            "- CONTRADICTED: evidence directly contradicts the claim\n"
            "- INSUFFICIENT: not enough evidence to assess\n"
            "- OUTDATED: claim was true but evidence suggests it has changed\n"
            "- UNVERIFIABLE: cannot be assessed from available sources"
        )

        try:
            raw = llm.complete(ASSESS_SYSTEM, user_prompt)
            data = json.loads(raw)
            for a in data.get("assessments", []):
                ci = a.get("claim_index")
                if ci is not None and 0 <= ci < len(batch_index_map):
                    results[batch_index_map[ci]] = a
        except (LLMParseError, Exception) as exc:
            logger.warning(f"Batched assessment LLM call failed: {exc}")

    assessed: list[ExtractedClaim] = []
    for i, claim in enumerate(claims):
        if i in no_source_indices:
            assessed.append(claim.model_copy(update={
                "assessment": "INSUFFICIENT",
                "assessment_rationale": "No relevant sources found for this claim.",
                "source_doc_count": 0,
                "independent_origin_count": 0,
                "llm_confidence": 0.0,
            }))
            continue

        relevant = claim_sources[i]
        a = results.get(i, {})

        assessment = a.get("assessment", "INSUFFICIENT").upper()
        if assessment not in _VALID_ASSESSMENTS:
            assessment = "INSUFFICIENT"

        supporting_ids: list[str] = a.get("supporting_source_ids", [])
        contradicting_ids: list[str] = a.get("contradicting_source_ids", [])

        evidence_records = [
            EvidenceRecord(
                evidence_id=f"ev-{uuid.uuid4().hex[:8]}",
                excerpt=s.snippet[:400],
                source_id=s.source_id,
                relevance=(
                    "SUPPORTING" if s.source_id in supporting_ids
                    else "CONTRADICTING" if s.source_id in contradicting_ids
                    else "CONTEXTUAL"
                ),
            )
            for s in relevant
        ]

        updated = claim.model_copy(update={
            "assessment": assessment,
            "assessment_rationale": a.get("rationale", ""),
            "evidence": evidence_records,
            "source_doc_count": len(relevant),
            "independent_origin_count": _count_independent_origins(
                [s.source_id for s in relevant], origins
            ),
            "llm_confidence": float(a.get("confidence", 0.0)),
        })
        updated = updated.model_copy(update={"is_stale": _is_stale(updated, sources)})
        assessed.append(updated)

    return assessed
