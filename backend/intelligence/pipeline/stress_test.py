"""Talking-point stress tester — batched.

1 LLM call to split ALL talking points into atomic claims.
1 LLM call to match ALL atomic claims against existing evidence.
1 LLM call to rewrite ALL matched talking points.
Total: 3 calls (was up to 3N+2 calls for N talking points).
"""

import json
import logging
from typing import Optional

from intelligence.contracts import (
    ExtractedClaim,
    SourceRecord,
    StressTestPointResult,
    StressTestResult,
)
from intelligence.providers.base import LLMParseError, LLMProvider

logger = logging.getLogger("changeradar.intelligence.pipeline.stress_test")

SPLIT_SYSTEM = (
    "You are a fact extractor. Split each talking point into atomic factual claims. "
    "Each claim must be a single, specific, verifiable statement. "
    "Return only valid JSON."
)

MATCH_SYSTEM = (
    "You are a fact matcher. For each atomic claim, find the best matching claim from "
    "the existing evidence ledger. Return only valid JSON."
)

REWRITE_SYSTEM = (
    "You are a communications advisor. For each talking point, rewrite it to be more "
    "accurate based on the matched evidence. Only rewrite if every fact is grounded in "
    "the evidence. Return only valid JSON."
)


def _batch_split(points: list[str], llm: LLMProvider) -> list[list[str]]:
    """Split all talking points into atomic claims in one call."""
    items = [{"point_index": i, "text": p} for i, p in enumerate(points)]
    user_prompt = (
        f"Talking points:\n{json.dumps(items, indent=2)}\n\n"
        'Return JSON: {"splits": [{"point_index": 0, "claims": ["...", "..."]}]}\n'
        "Each claim must be a single verifiable fact."
    )
    try:
        raw = llm.complete(SPLIT_SYSTEM, user_prompt)
        data = json.loads(raw)
        result = [""] * len(points)
        splits_map: dict[int, list[str]] = {}
        for s in data.get("splits", []):
            idx = s.get("point_index", 0)
            splits_map[idx] = [c for c in s.get("claims", []) if c.strip()]
        return [splits_map.get(i, [points[i]]) for i in range(len(points))]
    except (LLMParseError, Exception) as exc:
        logger.warning(f"Batched split failed: {exc}")
        return [[p] for p in points]


def _batch_match(
    atomic_claims_per_point: list[list[str]],
    existing_claims: list[ExtractedClaim],
    llm: LLMProvider,
) -> list[list[Optional[ExtractedClaim]]]:
    """Match all atomic claims against the evidence ledger in one call."""
    if not existing_claims:
        return [[None] * len(ac) for ac in atomic_claims_per_point]

    ledger = [{"claim_index": i, "text": c.text} for i, c in enumerate(existing_claims)]

    items = []
    for pi, atomic_claims in enumerate(atomic_claims_per_point):
        for ai, ac in enumerate(atomic_claims):
            items.append({"point_index": pi, "atomic_index": ai, "text": ac})

    user_prompt = (
        f"Evidence ledger:\n{json.dumps(ledger, indent=2)}\n\n"
        f"Atomic claims to match:\n{json.dumps(items, indent=2)}\n\n"
        'Return JSON: {"matches": [{"point_index": 0, "atomic_index": 0, '
        '"matched_claim_index": 2}]}\n'
        "Only include a match when the atomic claim and ledger claim assert the same specific fact. "
        "Omit entries where no match exists."
    )

    match_map: dict[tuple[int, int], int] = {}
    try:
        raw = llm.complete(MATCH_SYSTEM, user_prompt)
        data = json.loads(raw)
        for m in data.get("matches", []):
            pi = m.get("point_index")
            ai = m.get("atomic_index")
            ci = m.get("matched_claim_index")
            if pi is not None and ai is not None and ci is not None:
                if 0 <= ci < len(existing_claims):
                    match_map[(pi, ai)] = ci
    except (LLMParseError, Exception) as exc:
        logger.warning(f"Batched match failed: {exc}")

    result: list[list[Optional[ExtractedClaim]]] = []
    for pi, atomic_claims in enumerate(atomic_claims_per_point):
        row: list[Optional[ExtractedClaim]] = []
        for ai in range(len(atomic_claims)):
            ci = match_map.get((pi, ai))
            row.append(existing_claims[ci] if ci is not None else None)
        result.append(row)
    return result


def _batch_rewrite(
    points: list[str],
    matched_claims: list[Optional[ExtractedClaim]],
    sources: list[SourceRecord],
    llm: LLMProvider,
) -> list[Optional[str]]:
    """Generate grounded rewrites for all talking points in one call."""
    source_map = {s.source_id: s for s in sources}

    rewrite_eligible = []
    for i, (point, claim) in enumerate(zip(points, matched_claims)):
        if claim and claim.assessment in {"SUPPORTED", "PARTIALLY_SUPPORTED", "CONTRADICTED"}:
            evidence_items = [
                {
                    "excerpt": ev.excerpt,
                    "source": source_map[ev.source_id].publisher if ev.source_id in source_map else "unknown",
                    "relevance": ev.relevance,
                }
                for ev in claim.evidence[:3]
            ]
            rewrite_eligible.append({
                "point_index": i,
                "original": point,
                "assessment": claim.assessment,
                "evidence": evidence_items,
            })

    if not rewrite_eligible:
        return [None] * len(points)

    user_prompt = (
        f"Talking points to rewrite:\n{json.dumps(rewrite_eligible, indent=2)}\n\n"
        'Return JSON: {"rewrites": [{"point_index": 0, "suggested_wording": "..." or null}]}\n'
        "Only rewrite if every fact is grounded in the evidence. Return null otherwise."
    )

    rewrite_map: dict[int, Optional[str]] = {}
    try:
        raw = llm.complete(REWRITE_SYSTEM, user_prompt)
        data = json.loads(raw)
        for r in data.get("rewrites", []):
            pi = r.get("point_index")
            if pi is not None:
                rewrite_map[pi] = r.get("suggested_wording")
    except (LLMParseError, Exception) as exc:
        logger.warning(f"Batched rewrite failed: {exc}")

    return [rewrite_map.get(i) for i in range(len(points))]


def run(
    talking_points: list[str],
    existing_claims: list[ExtractedClaim],
    sources: list[SourceRecord],
    llm: LLMProvider,
) -> StressTestResult:
    """Assess all talking points in 3 batched LLM calls."""
    if not talking_points:
        return StressTestResult(points=[])

    # 1. Split all points into atomic claims — 1 call
    atomic_claims_per_point = _batch_split(talking_points, llm)

    # 2. Match all atomic claims against ledger — 1 call
    matches_per_point = _batch_match(atomic_claims_per_point, existing_claims, llm)

    # Best matched claim per point (first match found)
    best_match_per_point: list[Optional[ExtractedClaim]] = [
        next((m for m in matches if m is not None), None)
        for matches in matches_per_point
    ]

    # 3. Rewrite all eligible points — 1 call
    rewrites = _batch_rewrite(talking_points, best_match_per_point, sources, llm)

    results: list[StressTestPointResult] = []
    for i, point in enumerate(talking_points):
        matched = [m for m in matches_per_point[i] if m is not None]
        needs_more_research = any(m is None for m in matches_per_point[i])

        results.append(StressTestPointResult(
            original_point=point,
            extracted_claims=atomic_claims_per_point[i],
            assessments=matched,
            suggested_wording=rewrites[i],
            needs_more_research=needs_more_research,
        ))

    return StressTestResult(points=results)
