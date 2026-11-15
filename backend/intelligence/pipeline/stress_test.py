"""Talking-point stress tester — unified single-call assessment.

Rules (Stage H):
- Conditional: Only executed when user provides talking points.
- 1 single batched LLM call for all talking points.
- Reuses existing claims and evidence ledger rather than initiating duplicate research.
- Identifies contradictions, flags unsupported statements, and proposes grounded rewrites.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from intelligence.contracts import (
    ExtractedClaim,
    SourceRecord,
    StressTestPointResult,
    StressTestResult,
)
from intelligence.providers.base import LLMParseError, LLMProvider

logger = logging.getLogger("changeradar.intelligence.pipeline.stress_test")

STRESS_TEST_UNIFIED_SYSTEM = (
    "You are an executive meeting communications and evidence advisor.\n"
    "Your objective is to stress-test planned talking points against the verified evidence ledger.\n"
    "For each talking point:\n"
    "1. Identify the atomic factual assertions.\n"
    "2. Find matching claims from the provided evidence ledger.\n"
    "3. Check for direct contradictions (e.g., claiming 20% growth when evidence reports 14%, or permanent hire when search is ongoing).\n"
    "4. Provide a grounded suggested rewrite strictly anchored in the evidence, or null if evidence is insufficient.\n"
    "5. Indicate whether more research is needed.\n"
    "Return only valid JSON strictly matching the requested format."
)


def run(
    talking_points: List[str],
    existing_claims: List[ExtractedClaim],
    sources: List[SourceRecord],
    llm: LLMProvider,
) -> StressTestResult:
    """Evaluate all talking points against existing evidence in a single batched LLM call."""
    if not talking_points:
        return StressTestResult(points=[])

    # Build evidence ledger representation
    source_map = {s.source_id: s for s in sources}
    ledger = [
        {
            "claim_id": c.claim_id,
            "text": c.text,
            "assessment": c.assessment,
            "rationale": c.assessment_rationale,
            "evidence_excerpts": [
                {
                    "publisher": source_map[e.source_id].publisher if e.source_id in source_map else "Source",
                    "excerpt": e.excerpt[:250],
                    "relevance": e.relevance,
                }
                for e in c.evidence[:2]
            ],
        }
        for c in existing_claims
    ]

    points_payload = [{"point_index": i, "text": p} for i, p in enumerate(talking_points)]

    user_prompt = (
        f"Verified Evidence Ledger ({len(ledger)} claims):\n{json.dumps(ledger, indent=2)}\n\n"
        f"Planned Talking Points to Stress-Test:\n{json.dumps(points_payload, indent=2)}\n\n"
        "Return JSON in this structure:\n"
        "{\n"
        '  "evaluations": [\n'
        '    {\n'
        '      "point_index": 0,\n'
        '      "extracted_claims": ["Atomic factual statement"],\n'
        '      "matched_claim_ids": ["clm-..."],\n'
        '      "suggested_wording": "Grounded rewrite or null",\n'
        '      "needs_more_research": false\n'
        "    }\n"
        "  ]\n"
        "}\n"
    )

    claims_by_id = {c.claim_id: c for c in existing_claims}
    eval_map: Dict[int, Dict[str, Any]] = {}

    try:
        raw = llm.complete(STRESS_TEST_UNIFIED_SYSTEM, user_prompt, stage="stress_test")
        data = json.loads(raw)
        for ev in data.get("evaluations", []):
            idx = ev.get("point_index")
            if idx is not None:
                eval_map[idx] = ev
    except (LLMParseError, Exception) as exc:
        logger.warning(f"Unified stress test LLM call failed: {exc}")

    results: List[StressTestPointResult] = []

    for i, point in enumerate(talking_points):
        ev = eval_map.get(i)
        if not ev:
            # Fallback when LLM fails or omitted
            results.append(
                StressTestPointResult(
                    original_point=point,
                    extracted_claims=[point],
                    assessments=[],
                    suggested_wording=None,
                    needs_more_research=True,
                )
            )
            continue

        matched_claims = [
            claims_by_id[cid] for cid in ev.get("matched_claim_ids", []) if cid in claims_by_id
        ]
        extracted_facts = [f for f in ev.get("extracted_claims", []) if f.strip()] or [point]

        results.append(
            StressTestPointResult(
                original_point=point,
                extracted_claims=extracted_facts,
                assessments=matched_claims,
                suggested_wording=ev.get("suggested_wording"),
                needs_more_research=bool(ev.get("needs_more_research", not matched_claims)),
            )
        )

    return StressTestResult(points=results)
