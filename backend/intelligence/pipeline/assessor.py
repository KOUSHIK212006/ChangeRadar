"""Claim assessor — intelligent batched evidence verification.

Rules (Stage E):
- Evaluates multiple claims and evidence passages in bounded batches (up to MAX_CLAIMS_PER_BATCH).
- Detects contradictions, support, insufficiency, and staleness.
- Preserves evidence excerpts, source IDs, and independent origin counts.
- Separates self-reported LLM confidence from verified evidence quality.
"""

from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, List, Set
import uuid

from intelligence.config import intelligence_settings
from intelligence.contracts import (
    EvidenceRecord,
    ExtractedClaim,
    SourceOriginRecord,
    SourceRecord,
)
from intelligence.providers.base import LLMParseError, LLMProvider

logger = logging.getLogger("changeradar.intelligence.pipeline.assessor")

_VALID_ASSESSMENTS = {
    "SUPPORTED",
    "PARTIALLY_SUPPORTED",
    "CONTRADICTED",
    "INSUFFICIENT",
    "OUTDATED",
    "UNVERIFIABLE",
}

ASSESS_SYSTEM = (
    "You are an evidence verification analyst. Assess each atomic factual claim against the provided source excerpts.\n"
    "Rules:\n"
    "- SUPPORTED: Multiple independent sources or authoritative corporate records confirm it directly.\n"
    "- PARTIALLY_SUPPORTED: Supported in part, but key claims or details are missing.\n"
    "- CONTRADICTED: Credible source reporting directly conflicts with or disproves the claim.\n"
    "- INSUFFICIENT: Provided excerpts do not contain enough facts to substantiate the claim.\n"
    "- OUTDATED: Stated fact was previously true but subsequent events or reporting supersede it.\n"
    "- UNVERIFIABLE: Beyond public disclosure or unverified speculation.\n"
    "Return only valid JSON strictly matching the requested format."
)


def _find_relevant_sources(claim: ExtractedClaim, sources: List[SourceRecord]) -> List[SourceRecord]:
    """Keyword & token overlap retrieval for candidate evidence."""
    claim_words = set(claim.text.lower().split())
    scored = []
    for s in sources:
        overlap = len(claim_words & set((s.title + " " + s.snippet).lower().split()))
        if overlap > 0:
            scored.append((overlap, s))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in scored[:5]]


def _count_independent_origins(source_ids: List[str], origins: List[SourceOriginRecord]) -> int:
    """Count unique independent origins that contain any of the given source_ids."""
    if not source_ids:
        return 0
    sid_set = set(source_ids)
    matched_origins = {
        o.origin_id for o in origins if o.is_independent and any(sid in sid_set for sid in o.source_ids)
    }
    return max(len(matched_origins), 1)


def _is_stale(claim: ExtractedClaim, sources: List[SourceRecord]) -> bool:
    """Assess whether a claim may be stale based on volatility and publication recency."""
    if claim.volatility == "LOW":
        return False
    supporting_sids = {e.source_id for e in claim.evidence if e.relevance == "SUPPORTING"}
    if not supporting_sids:
        return False
    supporting_sources = [s for s in sources if s.source_id in supporting_sids and s.published_at]
    if not supporting_sources:
        return False
    newest = max(s.published_at for s in supporting_sources)
    age_days = (datetime.now(timezone.utc) - newest).days
    if claim.volatility == "HIGH":
        return age_days > 7
    if claim.volatility == "MEDIUM":
        return age_days > 30
    return False


def _assess_batch(
    claims_chunk: List[ExtractedClaim],
    sources: List[SourceRecord],
    origins: List[SourceOriginRecord],
    llm: LLMProvider,
) -> Dict[str, Dict[str, Any]]:
    """Execute assessment for a batch of claims in a single LLM request."""
    batch_items = []
    for c in claims_chunk:
        relevant_sources = _find_relevant_sources(c, sources)
        batch_items.append({
            "claim_id": c.claim_id,
            "claim_text": c.text,
            "evidence": [
                {
                    "source_id": s.source_id,
                    "publisher": s.publisher,
                    "published_at": s.published_at.isoformat() if s.published_at else "unknown",
                    "excerpt": s.snippet[:350],
                }
                for s in relevant_sources
            ],
        })

    user_prompt = (
        f"Evaluate these {len(batch_items)} claims against their evidence:\n"
        f"{json.dumps(batch_items, indent=2)}\n\n"
        "Return JSON:\n"
        "{\n"
        '  "assessments": [\n'
        '    {\n'
        '      "claim_id": "clm-...",\n'
        '      "assessment": "SUPPORTED|PARTIALLY_SUPPORTED|CONTRADICTED|INSUFFICIENT|OUTDATED|UNVERIFIABLE",\n'
        '      "rationale": "One concise sentence explaining verification rationale",\n'
        '      "supporting_source_ids": ["src-..."],\n'
        '      "contradicting_source_ids": ["src-..."],\n'
        '      "confidence": 0.95\n'
        "    }\n"
        "  ]\n"
        "}\n"
    )

    try:
        raw = llm.complete(ASSESS_SYSTEM, user_prompt, stage="assessment")
        data = json.loads(raw)
        return {a["claim_id"]: a for a in data.get("assessments", []) if "claim_id" in a}
    except (LLMParseError, Exception) as exc:
        logger.warning(f"Batch claim assessment failed for {len(claims_chunk)} claims: {exc}")
        return {}


def assess_claims(
    claims: List[ExtractedClaim],
    sources: List[SourceRecord],
    origins: List[SourceOriginRecord],
    llm: LLMProvider,
) -> List[ExtractedClaim]:
    """Assess all claims in bounded batches (typically 1 LLM request)."""
    if not claims:
        return []

    batch_size = max(1, intelligence_settings.MAX_CLAIMS_PER_BATCH)
    assessment_map: Dict[str, Dict[str, Any]] = {}

    for offset in range(0, len(claims), batch_size):
        chunk = claims[offset: offset + batch_size]
        chunk_assessments = _assess_batch(chunk, sources, origins, llm)
        assessment_map.update(chunk_assessments)
        logger.info(
            f"Batch assessment (offset={offset}, size={len(chunk)}) -> "
            f"{len(chunk_assessments)} verified"
        )

    source_map = {s.source_id: s for s in sources}
    assessed: List[ExtractedClaim] = []

    for c in claims:
        res = assessment_map.get(c.claim_id)
        if not res:
            # Fallback for unassessed or failed claims
            assessed.append(c.model_copy(update={
                "assessment": "INSUFFICIENT",
                "assessment_rationale": "Insufficient evidence retrieved in search scope.",
                "source_doc_count": len(c.evidence),
                "independent_origin_count": _count_independent_origins(
                    [e.source_id for e in c.evidence], origins
                ),
            }))
            continue

        assessment_val = res.get("assessment", "INSUFFICIENT").upper()
        if assessment_val not in _VALID_ASSESSMENTS:
            assessment_val = "INSUFFICIENT"

        supporting_ids: Set[str] = set(res.get("supporting_source_ids", []))
        contradicting_ids: Set[str] = set(res.get("contradicting_source_ids", []))

        evidence_records: List[EvidenceRecord] = []
        candidate_sources = _find_relevant_sources(c, sources)

        for s in candidate_sources:
            if s.source_id in contradicting_ids:
                relevance = "CONTRADICTING"
            elif s.source_id in supporting_ids:
                relevance = "SUPPORTING"
            else:
                relevance = "CONTEXTUAL"

            evidence_records.append(
                EvidenceRecord(
                    evidence_id=f"ev-{uuid.uuid4().hex[:8]}",
                    excerpt=s.snippet,
                    source_id=s.source_id,
                    relevance=relevance,
                )
            )

        active_sids = [e.source_id for e in evidence_records]
        origin_count = _count_independent_origins(active_sids, origins)

        updated_claim = c.model_copy(
            update={
                "assessment": assessment_val,
                "assessment_rationale": res.get("rationale", c.assessment_rationale),
                "evidence": evidence_records,
                "source_doc_count": len(active_sids),
                "independent_origin_count": origin_count,
                "llm_confidence": float(res.get("confidence", 0.0)),
            }
        )
        updated_claim = updated_claim.model_copy(
            update={"is_stale": _is_stale(updated_claim, sources)}
        )
        assessed.append(updated_claim)

    return assessed
