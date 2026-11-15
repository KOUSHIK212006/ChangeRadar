"""
Live pipeline test — runs the full intelligence engine against real APIs.
Run from backend/ directory:
    python live_pipeline_test.py
"""

import json
import logging
import sys
import os

# Load .env before importing anything from intelligence
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    stream=sys.stdout,
)

from intelligence.contracts import ResearchContext, ResearchRequest
from intelligence.engine import run_intelligence_engine

REQUEST = ResearchRequest(
    session_id="live-test-sess-001",
    job_id="live-test-job-001",
    context=ResearchContext(
        target_name="Anthropic",
        target_type="company",
        meeting_objective="Evaluate Anthropic as a potential AI infrastructure partner",
        time_window_days=30,
        research_questions=[
            "Any recent funding rounds or valuation changes?",
            "New model releases or product launches?",
            "Leadership or executive changes?",
            "Any regulatory or safety-related developments?",
        ],
        talking_points=[
            "Anthropic recently raised $4 billion from Google",
            "Claude 3 is the most capable model on the market",
        ],
    ),
    baseline=None,
)


def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def run():
    section("Running live intelligence pipeline")
    print(f"Target     : {REQUEST.context.target_name}")
    print(f"Objective  : {REQUEST.context.meeting_objective}")
    print(f"Time window: {REQUEST.context.time_window_days} days")

    result = run_intelligence_engine(REQUEST)

    section("STATUS")
    print(f"Status: {result.status}")
    print(f"Warnings ({len(result.warnings)}):")
    for w in result.warnings:
        print(f"  ⚠  {w}")

    section(f"SOURCES ({len(result.sources)})")
    for s in result.sources:
        syndicated = " [SYNDICATED]" if s.is_syndicated else ""
        print(f"  [{s.source_id}] {s.publisher}{syndicated}")
        print(f"    {s.title}")
        print(f"    published: {s.published_at}")

    section(f"ORIGINS ({len(result.origins)})")
    for o in result.origins:
        ind = "independent" if o.is_independent else "NOT independent"
        print(f"  [{o.origin_id}] {o.label} — {ind} (conf={o.independence_confidence:.2f})")
        print(f"    sources: {o.source_ids}")

    section(f"EVENTS ({len(result.events)})")
    for e in result.events:
        flags = []
        if e.is_disputed: flags.append("DISPUTED")
        if e.is_uncertain: flags.append("UNCERTAIN")
        flag_str = f" [{', '.join(flags)}]" if flags else ""
        print(f"  [{e.event_id}] [{e.lifecycle_status}]{flag_str}")
        print(f"    {e.title}")
        print(f"    event_at={e.event_at}  published_at={e.published_at}")
        print(f"    sources={e.source_ids}  claims={e.claim_ids}")

    section(f"CLAIMS ({len(result.claims)})")
    for c in result.claims:
        stale = " [STALE]" if c.is_stale else ""
        print(f"  [{c.claim_id}] [{c.assessment}]{stale} vol={c.volatility} conf={c.llm_confidence:.2f}")
        print(f"    {c.text}")
        print(f"    rationale: {c.assessment_rationale}")
        print(f"    sources={c.source_doc_count}  independent_origins={c.independent_origin_count}")
        for ev in c.evidence:
            print(f"    evidence [{ev.relevance}]: {ev.excerpt[:80]}...")

    section("COVERAGE")
    cov = result.coverage
    print(f"  Planned={cov.planned_searches}  Executed={cov.executed_searches}  Failed={cov.failed_searches}")
    print(f"  Time window: {cov.time_window_days} days")
    print(f"  Source types: {cov.source_types_found}")
    print(f"  Origin diversity score: {cov.origin_diversity_score:.2f}")
    print(f"  Gaps ({len(cov.gaps)}):")
    for g in cov.gaps:
        print(f"    - {g}")
    print(f"  Coverage warnings ({len(cov.warnings)}):")
    for w in cov.warnings:
        print(f"    ⚠  {w}")

    section("DELTA")
    if result.delta is None:
        print("  None (first run — no baseline supplied)")
    else:
        d = result.delta
        print(f"  new_events: {d.new_events}")
        print(f"  updated_events: {d.updated_events}")
        print(f"  new_evidence_for_claims: {d.new_evidence_for_claims}")
        print(f"  changed_assessments: {d.changed_assessments}")
        print(f"  no_material_change: {d.no_material_change}")
        print(f"  comparison_incomplete: {d.comparison_incomplete}")

    section(f"STRESS TEST ({len(result.stress_test.points) if result.stress_test else 0} points)")
    if result.stress_test:
        for pt in result.stress_test.points:
            print(f"\n  Point: \"{pt.original_point}\"")
            print(f"  Extracted claims: {pt.extracted_claims}")
            print(f"  Needs more research: {pt.needs_more_research}")
            for a in pt.assessments:
                print(f"  Assessment: [{a.assessment}] {a.text}")
                print(f"    rationale: {a.assessment_rationale}")
            if pt.suggested_wording:
                print(f"  Suggested wording: \"{pt.suggested_wording}\"")
            else:
                print(f"  Suggested wording: None")

    section("PROVIDER METADATA")
    print(json.dumps(result.provider_metadata, indent=2))

    section("SUMMARY")
    print(f"  Status            : {result.status}")
    print(f"  Sources           : {len(result.sources)}")
    print(f"  Origins           : {len(result.origins)}")
    print(f"  Events            : {len(result.events)}")
    print(f"  Event versions    : {len(result.event_versions)}")
    print(f"  Claims            : {len(result.claims)}")
    print(f"  Coverage gaps     : {len(result.coverage.gaps)}")
    print(f"  Stress test points: {len(result.stress_test.points) if result.stress_test else 0}")
    print(f"  Warnings          : {len(result.warnings)}")

    # Basic assertions
    assert result.session_id == REQUEST.session_id
    assert result.job_id == REQUEST.job_id
    assert result.status in {"COMPLETED", "PARTIAL", "FAILED"}
    assert result.coverage is not None
    assert result.delta is None  # no baseline supplied
    for claim in result.claims:
        assert claim.assessment in {
            "SUPPORTED", "PARTIALLY_SUPPORTED", "CONTRADICTED",
            "INSUFFICIENT", "OUTDATED", "UNVERIFIABLE"
        }, f"Invalid assessment: {claim.assessment}"
        assert claim.independent_origin_count <= claim.source_doc_count, \
            f"Origin count {claim.independent_origin_count} > source count {claim.source_doc_count}"

    print("\n✅ All assertions passed.")


if __name__ == "__main__":
    run()
