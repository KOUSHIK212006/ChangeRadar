"""Research processor interface, intelligence engine processor, and mock implementation."""

import logging
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Protocol

from app.models.enums import EvidenceVerificationStatus, ResearchResultStatus
from app.models.research_job import ResearchJob
from app.models.research_result import ResearchResult
from app.models.research_session import ResearchSession

logger = logging.getLogger("changeradar.worker.processor")

ProgressCallback = Callable[[str, int], None]


class ResearchProcessor(Protocol):
    """Protocol for research execution engines."""

    def process(
        self,
        job: ResearchJob,
        session: ResearchSession,
        on_progress: Optional[ProgressCallback] = None,
    ) -> ResearchResult:
        """Execute research and return a synthesized ResearchResult."""
        ...


class IntelligenceEngineProcessor:
    """Calls run_intelligence_engine() and maps IntelligenceResult → ResearchResult."""

    def process(
        self,
        job: ResearchJob,
        session: ResearchSession,
        on_progress: Optional[ProgressCallback] = None,
    ) -> ResearchResult:
        from intelligence.contracts import (
            BaselineClaimSnapshot,
            BaselineEventSnapshot,
            ResearchBaseline,
            ResearchContext,
            ResearchRequest,
        )
        from intelligence.engine import run_intelligence_engine

        def _progress(stage: str, percent: int) -> None:
            if on_progress:
                on_progress(stage, percent)

        _progress("building_request", 5)

        # Parse time_window string (e.g. "30 days") into an integer day count
        time_window_days = 30
        if session.time_window:
            try:
                time_window_days = int("".join(filter(str.isdigit, session.time_window))) or 30
            except (ValueError, TypeError):
                pass

        # Build baseline from last reviewed result if available
        baseline = None
        if session.last_reviewed_result_id and session.last_reviewed_result:
            reviewed = session.last_reviewed_result
            event_snapshots = []
            claim_snapshots = []

            for ev in (reviewed.key_developments or []):
                if ev.get("event_id"):
                    event_snapshots.append(BaselineEventSnapshot(
                        event_id=ev["event_id"],
                        description=ev.get("description", ""),
                        lifecycle_status=ev.get("lifecycle_status", "NEW"),
                    ))

            for cl in (reviewed.claims_and_evidence or []):
                if cl.get("claim_id"):
                    claim_snapshots.append(BaselineClaimSnapshot(
                        claim_id=cl["claim_id"],
                        assessment=cl.get("assessment", "INSUFFICIENT"),
                    ))

            baseline = ResearchBaseline(
                baseline_result_id=str(reviewed.id),
                reviewed_at=session.last_reviewed_at or reviewed.reviewed_at or reviewed.created_at,
                known_event_ids=[s.event_id for s in event_snapshots],
                known_claim_ids=[s.claim_id for s in claim_snapshots],
                event_snapshots=event_snapshots,
                claim_snapshots=claim_snapshots,
            )

        request = ResearchRequest(
            session_id=str(session.id),
            job_id=str(job.id),
            context=ResearchContext(
                target_name=session.target_name,
                target_type=session.target_type,
                meeting_objective=session.meeting_context or "General research briefing",
                time_window_days=time_window_days,
                research_questions=session.research_questions or [],
                talking_points=session.talking_points or [],
            ),
            baseline=baseline,
        )

        _progress("running_intelligence_engine", 10)
        intelligence_result = run_intelligence_engine(request)
        _progress("persisting_result", 90)

        # Map IntelligenceResult → ResearchResult (backend's persistence model)
        status_map = {
            "COMPLETED": ResearchResultStatus.COMPLETED,
            "PARTIAL": ResearchResultStatus.PARTIAL,
            "FAILED": ResearchResultStatus.PARTIAL,
        }
        research_status = status_map.get(intelligence_result.status, ResearchResultStatus.PARTIAL)

        return ResearchResult(
            session_id=session.id,
            job_id=job.id,
            research_status=research_status,
            summary=_build_summary(intelligence_result),
            key_developments=[e.model_dump(mode="json") for e in intelligence_result.events],
            sources=[s.model_dump(mode="json") for s in intelligence_result.sources],
            claims_and_evidence=[c.model_dump(mode="json") for c in intelligence_result.claims],
            coverage_report=intelligence_result.coverage.model_dump(mode="json"),
            talking_points_analysis=(
                [p.model_dump(mode="json") for p in intelligence_result.stress_test.points]
                if intelligence_result.stress_test else []
            ),
            is_delta=intelligence_result.delta is not None,
            delta_summary=intelligence_result.delta.model_dump(mode="json") if intelligence_result.delta else None,
            raw_intelligence=intelligence_result.model_dump(mode="json"),
            is_reviewed=False,
        )


def _build_summary(result: Any) -> str:
    """Build a human-readable summary from the intelligence result."""
    event_count = len(result.events)
    claim_count = len(result.claims)
    source_count = len(result.sources)
    origin_count = len(result.origins)
    gaps = result.coverage.gaps

    lines = [
        f"Research completed for: {result.provider_metadata.get('run_at', 'unknown time')}",
        f"Found {event_count} event(s), {claim_count} claim(s) across {source_count} source(s) "
        f"from {origin_count} origin(s).",
    ]
    if gaps:
        lines.append(f"Coverage gaps: {'; '.join(gaps[:3])}.")
    if result.warnings:
        lines.append(f"Warnings: {'; '.join(result.warnings[:3])}.")
    return "\n".join(lines)


class MockResearchProcessor:
    """Mock research engine producing realistic, evidence-first intelligence briefings."""

    def __init__(self, simulate_delay: float = 0.0):
        self.simulate_delay = simulate_delay

    def _report_progress(self, callback: Optional[ProgressCallback], stage: str, percent: int) -> None:
        if callback:
            callback(stage, percent)
        if self.simulate_delay > 0:
            time.sleep(self.simulate_delay)

    def process(
        self,
        job: ResearchJob,
        session: ResearchSession,
        on_progress: Optional[ProgressCallback] = None,
    ) -> ResearchResult:
        """Simulate the multi-stage intelligence pipeline and produce a complete briefing."""
        target = session.target_name
        meeting_context = session.meeting_context or "General strategic briefing"

        # Stage 1: Context Resolution
        self._report_progress(on_progress, "resolving_context", 15)

        # Stage 2: Search Planning & Query Formulation
        self._report_progress(on_progress, "planning_searches", 35)

        # Stage 3: Source Retrieval & Origin Normalization
        self._report_progress(on_progress, "retrieving_sources", 55)

        sources: List[Dict[str, Any]] = [
            {
                "id": str(uuid.uuid4()),
                "title": f"Recent Corporate Disclosures and Market Movements for {target}",
                "url": f"https://news.example.com/{target.lower().replace(' ', '-')}-filings",
                "publisher": "Financial Gazette",
                "published_at": "2026-11-01T12:00:00Z",
                "origin_cluster_id": "cluster-origin-1",
                "origin_type": "official_disclosure",
            },
            {
                "id": str(uuid.uuid4()),
                "title": f"{target} Leadership and Strategic Product Initiatives Update",
                "url": f"https://tech.example.com/{target.lower().replace(' ', '-')}-product-roadmap",
                "publisher": "Tech Wire",
                "published_at": "2026-11-08T09:30:00Z",
                "origin_cluster_id": "cluster-origin-2",
                "origin_type": "industry_press",
            },
            {
                "id": str(uuid.uuid4()),
                "title": f"Independent Analyst Assessment of {target}'s Expansion",
                "url": f"https://marketresearch.example.com/analysis/{target.lower().replace(' ', '-')}",
                "publisher": "Alpha Capital Research",
                "published_at": "2026-11-12T14:15:00Z",
                "origin_cluster_id": "cluster-origin-3",
                "origin_type": "analyst_report",
            },
        ]

        # Stage 4: Event Extraction & Claim Clustering
        self._report_progress(on_progress, "extracting_events_and_claims", 75)

        key_developments: List[Dict[str, Any]] = [
            {
                "id": f"dev-{uuid.uuid4().hex[:8]}",
                "title": f"Strategic Expansion and New Partnerships Announced by {target}",
                "description": f"{target} has formalized enterprise agreements in key growth regions.",
                "event_date": "2026-11-05",
                "status": "DEVELOPING",
                "sources": [sources[0]["id"], sources[1]["id"]],
            },
            {
                "id": f"dev-{uuid.uuid4().hex[:8]}",
                "title": f"Executive Leadership and Operational Realignment",
                "description": f"Internal restructuring to optimize enterprise delivery and partner channels.",
                "event_date": "2026-10-28",
                "status": "COMPLETED",
                "sources": [sources[1]["id"]],
            },
        ]

        claims_and_evidence: List[Dict[str, Any]] = [
            {
                "id": f"claim-{uuid.uuid4().hex[:8]}",
                "claim": f"{target} expanded into international markets with new enterprise pilots.",
                "verification_status": EvidenceVerificationStatus.SUPPORTED.value,
                "rationale": "Directly confirmed by official regulatory filings and partner announcements.",
                "evidence": "Filing indicates 3 enterprise pilots launched in October 2026.",
                "source_urls": [sources[0]["url"]],
            },
            {
                "id": f"claim-{uuid.uuid4().hex[:8]}",
                "claim": f"{target} has fully replaced its core platform infrastructure.",
                "verification_status": EvidenceVerificationStatus.PARTIALLY_SUPPORTED.value,
                "rationale": "Migration is underway across pilot accounts, but full platform rollout is ongoing.",
                "evidence": "Analyst report notes progressive rollout across Q4.",
                "source_urls": [sources[2]["url"]],
            },
            {
                "id": f"claim-{uuid.uuid4().hex[:8]}",
                "claim": f"{target} announced imminent plans for an initial public offering.",
                "verification_status": EvidenceVerificationStatus.CONTRADICTED.value,
                "rationale": "Leadership explicitly denied near-term IPO speculation in public remarks.",
                "evidence": "Official statement explicitly refuted IPO timing rumors.",
                "source_urls": [sources[1]["url"]],
            },
        ]

        # Stage 5: Talking Points Stress-Testing (if supplied)
        talking_points_analysis: List[Dict[str, Any]] = []
        if session.talking_points:
            for pt in session.talking_points:
                talking_points_analysis.append({
                    "original_talking_point": pt,
                    "extracted_claim": pt,
                    "verification_status": EvidenceVerificationStatus.SUPPORTED.value,
                    "assessment": f"Grounding verified against current research for {target}.",
                    "suggested_wording": f"{pt} (as confirmed by recent Q4 disclosures).",
                    "sources": [sources[0]["url"]],
                })

        coverage_report: Dict[str, Any] = {
            "searches_planned": 4,
            "searches_executed": 4,
            "sources_evaluated": 12,
            "independent_origins_identified": 3,
            "known_gaps": [],
            "limitations": "Data limited to publicly accessible filings and industry press up to discovery date.",
        }

        # Stage 6: Briefing Synthesis
        self._report_progress(on_progress, "synthesizing_briefing", 95)

        summary = (
            f"Pre-Meeting Research Briefing for {target}\n\n"
            f"Context: {meeting_context}\n\n"
            f"Key Takeaways:\n"
            f"1. {target} demonstrates active enterprise expansion with documented regulatory filings.\n"
            f"2. Recent platform restructuring is showing measured adoption in pilot environments.\n"
            f"3. Claims regarding near-term IPO remain unsubstantiated and contradict official statements.\n"
            f"Confidence: High evidence traceability across 3 independent publisher origins."
        )

        result = ResearchResult(
            session_id=session.id,
            job_id=job.id,
            research_status=ResearchResultStatus.COMPLETED,
            summary=summary,
            key_developments=key_developments,
            sources=sources,
            claims_and_evidence=claims_and_evidence,
            coverage_report=coverage_report,
            talking_points_analysis=talking_points_analysis,
            is_delta=False,
            is_reviewed=False,
            raw_intelligence={
                "engine": "MockResearchEngine-v1",
                "target": target,
                "execution_timestamp": time.time(),
            },
        )

        return result

