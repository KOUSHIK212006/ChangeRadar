"""Research processor interface, intelligence engine processor, and mock implementation."""

from datetime import datetime, timezone
import logging
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Protocol

from app.models.enums import EvidenceVerificationStatus, ResearchResultStatus
from app.models.research_job import ResearchJob
from app.models.research_result import ResearchResult
from app.models.research_session import ResearchSession
from intelligence.contracts import (
    ClaimVolatility,
    CoverageReport,
    EngineResultStatus,
    EventLifecycle,
    EvidenceAssessment,
    EvidenceRecord,
    EvidenceStance,
    ExtractedClaim,
    ExtractedEvent,
    IntelligenceResult,
    SourceOriginRecord,
    SourceRecord,
    StressTestPointResult,
    StressTestResult,
)

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
    if getattr(result, "briefing_summary", None):
        return result.briefing_summary

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
        now = datetime.now(timezone.utc)
        slug = target.lower().replace(" ", "-")

        # Parse time_window string (e.g. "30 days") into an integer day count
        time_window_days = 30
        if session.time_window:
            try:
                time_window_days = int("".join(filter(str.isdigit, session.time_window))) or 30
            except (ValueError, TypeError):
                pass

        # Stage 1: Context Resolution
        self._report_progress(on_progress, "resolving_context", 15)

        # Stage 2: Search Planning & Query Formulation
        self._report_progress(on_progress, "planning_searches", 35)

        # Stage 3: Source Retrieval & Origin Normalization
        self._report_progress(on_progress, "retrieving_sources", 55)

        sources_records: List[SourceRecord] = [
            SourceRecord(
                source_id="src-mock-001",
                url=f"https://news.example.com/{slug}-filings",
                canonical_url=f"https://news.example.com/{slug}-filings",
                title=f"Recent Corporate Disclosures and Market Movements for {target}",
                publisher="Financial Gazette",
                snippet=f"Official regulatory disclosures confirm {target} ongoing market operations and strategic expansion.",
                published_at=now,
                discovered_at=now,
                is_syndicated=False,
                syndication_confidence=0.0,
            ),
            SourceRecord(
                source_id="src-mock-002",
                url=f"https://tech.example.com/{slug}-product-roadmap",
                canonical_url=f"https://tech.example.com/{slug}-product-roadmap",
                title=f"{target} Leadership and Strategic Product Initiatives Update",
                publisher="Tech Wire",
                snippet=f"{target} has formalized enterprise delivery and partner channels across active regions.",
                published_at=now,
                discovered_at=now,
                is_syndicated=False,
                syndication_confidence=0.0,
            ),
            SourceRecord(
                source_id="src-mock-003",
                url=f"https://marketresearch.example.com/analysis/{slug}",
                canonical_url=f"https://marketresearch.example.com/analysis/{slug}",
                title=f"Independent Analyst Assessment of {target}'s Expansion",
                publisher="Alpha Capital Research",
                snippet=f"Analyst review highlights measured enterprise rollout and capital allocation for {target}.",
                published_at=now,
                discovered_at=now,
                is_syndicated=False,
                syndication_confidence=0.0,
            ),
        ]

        origins_records: List[SourceOriginRecord] = [
            SourceOriginRecord(
                origin_id="org-mock-001",
                label=f"{target} Official Disclosures",
                source_ids=["src-mock-001"],
                is_independent=False,
                independence_confidence=0.9,
            ),
            SourceOriginRecord(
                origin_id="org-mock-002",
                label="Tech Wire Industry Reporting",
                source_ids=["src-mock-002"],
                is_independent=True,
                independence_confidence=0.95,
            ),
            SourceOriginRecord(
                origin_id="org-mock-003",
                label="Alpha Capital Analyst Report",
                source_ids=["src-mock-003"],
                is_independent=True,
                independence_confidence=0.95,
            ),
        ]

        # Stage 4: Event Extraction & Claim Clustering
        self._report_progress(on_progress, "extracting_events_and_claims", 75)

        events_records: List[ExtractedEvent] = [
            ExtractedEvent(
                event_id="evt-mock-001",
                title=f"Strategic Expansion and New Partnerships Announced by {target}",
                description=f"{target} has formalized enterprise agreements and partner integrations in key growth markets.",
                summary=f"{target} expanded enterprise partner initiatives.",
                category="EXPANSION",
                lifecycle_status=EventLifecycle.DEVELOPING,
                event_at=now,
                published_at=now,
                discovered_at=now,
                is_disputed=False,
                is_uncertain=False,
                source_ids=["src-mock-001", "src-mock-002"],
                origin_ids=["org-mock-001", "org-mock-002"],
                claim_ids=["clm-mock-001", "clm-mock-002"],
            ),
            ExtractedEvent(
                event_id="evt-mock-002",
                title=f"Executive Leadership and Operational Realignment",
                description=f"Internal restructuring to optimize enterprise delivery and partner channels at {target}.",
                summary=f"Leadership realignment at {target}.",
                category="LEADERSHIP",
                lifecycle_status=EventLifecycle.COMPLETED,
                event_at=now,
                published_at=now,
                discovered_at=now,
                is_disputed=False,
                is_uncertain=False,
                source_ids=["src-mock-002"],
                origin_ids=["org-mock-002"],
                claim_ids=["clm-mock-002"],
            ),
        ]

        claims_records: List[ExtractedClaim] = [
            ExtractedClaim(
                claim_id="clm-mock-001",
                text=f"{target} expanded into international markets with new enterprise pilots.",
                assessment=EvidenceAssessment.SUPPORTED,
                assessment_rationale="Directly confirmed by official regulatory filings and partner announcements.",
                evidence=[
                    EvidenceRecord(
                        evidence_id="ev-mock-001",
                        excerpt=f"Filing indicates 3 enterprise pilots launched in October 2026 for {target}.",
                        source_id="src-mock-001",
                        relevance=EvidenceStance.SUPPORTING,
                    )
                ],
                source_doc_count=2,
                independent_origin_count=2,
                volatility=ClaimVolatility.LOW,
                is_stale=False,
                llm_confidence=0.95,
            ),
            ExtractedClaim(
                claim_id="clm-mock-002",
                text=f"{target} has fully replaced its core platform infrastructure.",
                assessment=EvidenceAssessment.PARTIALLY_SUPPORTED,
                assessment_rationale="Migration is underway across pilot accounts, but full platform rollout is ongoing.",
                evidence=[
                    EvidenceRecord(
                        evidence_id="ev-mock-002",
                        excerpt="Analyst report notes progressive rollout across Q4.",
                        source_id="src-mock-003",
                        relevance=EvidenceStance.CONTEXTUAL,
                    )
                ],
                source_doc_count=1,
                independent_origin_count=1,
                volatility=ClaimVolatility.MEDIUM,
                is_stale=False,
                llm_confidence=0.88,
            ),
            ExtractedClaim(
                claim_id="clm-mock-003",
                text=f"{target} announced imminent plans for an initial public offering.",
                assessment=EvidenceAssessment.CONTRADICTED,
                assessment_rationale="Leadership explicitly denied near-term IPO speculation in public remarks.",
                evidence=[
                    EvidenceRecord(
                        evidence_id="ev-mock-003",
                        excerpt="Official statement explicitly refuted IPO timing rumors.",
                        source_id="src-mock-002",
                        relevance=EvidenceStance.CONTRADICTING,
                    )
                ],
                source_doc_count=1,
                independent_origin_count=1,
                volatility=ClaimVolatility.HIGH,
                is_stale=False,
                llm_confidence=0.92,
            ),
        ]

        coverage_report = CoverageReport(
            planned_searches=4,
            executed_searches=4,
            failed_searches=0,
            time_window_days=time_window_days,
            source_types_found=["official_disclosure", "industry_press", "analyst_report"],
            origin_diversity_score=1.0,
            gaps=[],
            warnings=[],
        )

        # Stage 5: Talking Points Stress-Testing (if supplied)
        stress_test: Optional[StressTestResult] = None
        if session.talking_points:
            points: List[StressTestPointResult] = []
            for pt in session.talking_points:
                points.append(
                    StressTestPointResult(
                        original_point=pt,
                        extracted_claims=[pt],
                        assessments=[claims_records[0]],
                        suggested_wording=f"{pt} (as confirmed by recent Q4 disclosures).",
                        needs_more_research=False,
                    )
                )
            stress_test = StressTestResult(points=points)

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

        # Build fully valid typed IntelligenceResult matching contracts schema
        intelligence_result = IntelligenceResult(
            session_id=str(session.id),
            job_id=str(job.id),
            status=EngineResultStatus.COMPLETED,
            briefing_summary=summary,
            sources=sources_records,
            origins=origins_records,
            events=events_records,
            event_versions=[],
            claims=claims_records,
            coverage=coverage_report,
            delta=None,
            stress_test=stress_test,
            warnings=[],
            provider_metadata={
                "engine": "MockResearchProcessor",
                "target": target,
                "run_at": now.isoformat(),
            },
        )

        # Map into dual-compatible dictionaries for both API response models:
        key_developments = []
        for e in intelligence_result.events:
            d = e.model_dump(mode="json")
            d["id"] = e.event_id
            d["event_date"] = e.event_at.strftime("%Y-%m-%d") if e.event_at else "2026-11-05"
            d["status"] = e.lifecycle_status
            d["sources"] = e.source_ids
            key_developments.append(d)

        claims_and_evidence = []
        for c in intelligence_result.claims:
            d = c.model_dump(mode="json")
            d["id"] = c.claim_id
            d["claim"] = c.text
            d["verification_status"] = c.assessment
            d["rationale"] = c.assessment_rationale
            d["evidence"] = c.evidence[0].excerpt if c.evidence else ""
            d["source_urls"] = [s.url for s in sources_records if s.source_id in [ev.source_id for ev in c.evidence]]
            claims_and_evidence.append(d)

        sources_list = []
        for s in intelligence_result.sources:
            d = s.model_dump(mode="json")
            d["id"] = s.source_id
            sources_list.append(d)

        talking_points_analysis = []
        if intelligence_result.stress_test:
            for p in intelligence_result.stress_test.points:
                d = p.model_dump(mode="json")
                d["original_talking_point"] = p.original_point
                d["extracted_claim"] = p.extracted_claims[0] if p.extracted_claims else p.original_point
                d["verification_status"] = EvidenceVerificationStatus.SUPPORTED.value
                d["assessment"] = f"Grounding verified against current research for {target}."
                talking_points_analysis.append(d)

        result = ResearchResult(
            session_id=session.id,
            job_id=job.id,
            research_status=ResearchResultStatus.COMPLETED,
            summary=summary,
            key_developments=key_developments,
            sources=sources_list,
            claims_and_evidence=claims_and_evidence,
            coverage_report=coverage_report.model_dump(mode="json"),
            talking_points_analysis=talking_points_analysis,
            is_delta=False,
            is_reviewed=False,
            raw_intelligence=intelligence_result.model_dump(mode="json"),
        )

        return result
