"""Pydantic contracts for the intelligence engine — input, output, and all intermediate types.

These are the shared contracts between the intelligence engine (Surjith),
the backend worker (Krishank), and the API response shapes (Koushik).

Rules:
- No SQLAlchemy imports.
- No FastAPI imports.
- No database session usage.
- EvidenceVerificationStatus values mirror app/models/enums.py exactly.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums as string literals (mirrors app/models/enums.py — do not rename)
# ---------------------------------------------------------------------------

class EvidenceAssessment:
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    INSUFFICIENT = "INSUFFICIENT"
    OUTDATED = "OUTDATED"
    UNVERIFIABLE = "UNVERIFIABLE"


class EventLifecycle:
    NEW = "NEW"
    DEVELOPING = "DEVELOPING"
    UPDATED = "UPDATED"
    COMPLETED = "COMPLETED"


class ClaimVolatility:
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class EvidenceStance:
    SUPPORTING = "SUPPORTING"
    CONTRADICTING = "CONTRADICTING"
    CONTEXTUAL = "CONTEXTUAL"


class EngineResultStatus:
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


# ---------------------------------------------------------------------------
# Input contracts
# ---------------------------------------------------------------------------

class ResearchContext(BaseModel):
    """User-supplied research context passed from the backend worker."""

    target_name: str = Field(..., description="Name of the company, person, or topic being researched")
    target_type: Optional[str] = Field(None, description="e.g. company, person, market, topic")
    meeting_objective: str = Field(..., description="Purpose of the upcoming meeting")
    time_window_days: int = Field(30, ge=1, le=365, description="How far back to search in days")
    research_questions: list[str] = Field(default_factory=list, description="Specific questions to answer")
    talking_points: list[str] = Field(default_factory=list, description="Talking points to stress-test")


class BaselineEventSnapshot(BaseModel):
    """Snapshot of a single event at review time — used for material change detection."""
    event_id: str
    description: str
    lifecycle_status: str


class BaselineClaimSnapshot(BaseModel):
    """Snapshot of a single claim's assessment at review time — used for changed-assessment detection."""
    claim_id: str
    assessment: str


class ResearchBaseline(BaseModel):
    """Snapshot of the user's last reviewed state — used for delta computation."""

    baseline_result_id: str = Field(..., description="ID of the previously reviewed IntelligenceResult")
    reviewed_at: datetime = Field(..., description="UTC timestamp when the user marked it reviewed")
    known_event_ids: list[str] = Field(default_factory=list, description="Event IDs present at review time")
    known_claim_ids: list[str] = Field(default_factory=list, description="Claim IDs present at review time")
    event_snapshots: list[BaselineEventSnapshot] = Field(default_factory=list, description="Event descriptions at review time — enables LLM material change detection")
    claim_snapshots: list[BaselineClaimSnapshot] = Field(default_factory=list, description="Claim assessments at review time — enables changed-assessment detection")


class ResearchRequest(BaseModel):
    """Top-level input to run_intelligence_engine(). Constructed by the backend worker."""

    session_id: str = Field(..., description="ResearchSession.id from the backend")
    job_id: str = Field(..., description="ResearchJob.id from the backend")
    context: ResearchContext
    baseline: Optional[ResearchBaseline] = Field(None, description="None on first run; set on subsequent runs")


# ---------------------------------------------------------------------------
# Source and origin contracts
# ---------------------------------------------------------------------------

class SourceRecord(BaseModel):
    """A single retrieved source document, normalised from a search provider result."""

    source_id: str = Field(..., description="sha256(canonical_url)[:16] — stable identifier")
    url: str
    canonical_url: str = Field(..., description="URL with UTM params stripped and trailing slash removed")
    title: str
    publisher: str
    snippet: str = Field(..., description="Relevant excerpt from the document")
    published_at: Optional[datetime] = Field(None, description="When the source was published (UTC)")
    discovered_at: datetime = Field(..., description="When the engine retrieved this source (UTC)")
    is_syndicated: bool = Field(False, description="True if this appears to be a republication of another source")
    syndication_confidence: float = Field(0.0, ge=0.0, le=1.0)


class SourceOriginRecord(BaseModel):
    """A canonical origin cluster — one press release republished by 10 outlets = one origin."""

    origin_id: str = Field(..., description="sha256(label)[:16]")
    label: str = Field(..., description="Human-readable origin label e.g. 'Reuters', 'Company Press Release'")
    source_ids: list[str] = Field(..., description="All source_ids belonging to this origin")
    is_independent: bool = Field(..., description="True if this origin is editorially independent")
    independence_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in independence classification — be conservative")


# ---------------------------------------------------------------------------
# Event contracts
# ---------------------------------------------------------------------------

class ExtractedEvent(BaseModel):
    """A normalised real-world development extracted and clustered from sources."""

    event_id: str = Field(..., description="sha256(canonical_title)[:16]")
    title: str
    description: str
    lifecycle_status: str = Field(..., description="EventLifecycle constant")
    is_disputed: bool = False
    is_uncertain: bool = False
    event_at: Optional[datetime] = Field(None, description="When the described event happened (UTC) — may differ from published_at")
    published_at: Optional[datetime] = Field(None, description="When the earliest source covering this event was published (UTC)")
    discovered_at: datetime = Field(..., description="When the engine first found this event (UTC)")
    source_ids: list[str] = Field(default_factory=list)
    origin_ids: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)


class EventVersionRecord(BaseModel):
    """A timestamped change to an event's known description or status."""

    version_id: str
    event_id: str
    description: str = Field(..., description="Full event description at this version")
    changed_at: datetime = Field(..., description="UTC timestamp of this version")
    change_summary: str = Field(..., description="One-sentence summary of what changed")


# ---------------------------------------------------------------------------
# Claim and evidence contracts
# ---------------------------------------------------------------------------

class EvidenceRecord(BaseModel):
    """A single piece of evidence linked to a claim."""

    evidence_id: str
    excerpt: str = Field(..., description="Verbatim or near-verbatim excerpt from the source")
    source_id: str
    relevance: str = Field(..., description="EvidenceStance constant: SUPPORTING | CONTRADICTING | CONTEXTUAL")


class ExtractedClaim(BaseModel):
    """An atomic factual claim extracted from events, with evidence assessment."""

    claim_id: str
    text: str = Field(..., description="Single verifiable factual statement — not a paragraph")
    assessment: str = Field(..., description="EvidenceAssessment constant")
    assessment_rationale: str = Field(..., description="One-sentence explanation of the assessment")
    evidence: list[EvidenceRecord] = Field(default_factory=list)
    source_doc_count: int = Field(..., description="Number of source documents referencing this claim")
    independent_origin_count: int = Field(..., description="Conservative estimate of independent origins — not article count")
    volatility: str = Field(..., description="ClaimVolatility constant: LOW | MEDIUM | HIGH")
    is_stale: bool = Field(False, description="True if claim may no longer be current given its volatility and source age")
    llm_confidence: float = Field(..., ge=0.0, le=1.0, description="LLM self-reported confidence — stored separately, never used as assessment")


# ---------------------------------------------------------------------------
# Delta contract
# ---------------------------------------------------------------------------

class DeltaRecord(BaseModel):
    """Change summary relative to the user's last reviewed baseline."""

    new_events: list[str] = Field(default_factory=list, description="event_ids not present in baseline")
    updated_events: list[str] = Field(default_factory=list, description="event_ids present in baseline with material description/status change")
    new_evidence_for_claims: list[str] = Field(default_factory=list, description="claim_ids that have new evidence since baseline")
    changed_assessments: list[str] = Field(default_factory=list, description="claim_ids whose assessment status changed since baseline")
    no_material_change: bool = Field(False, description="True when comparison is complete and nothing meaningful changed")
    comparison_incomplete: bool = Field(False, description="True when the current run or baseline is PARTIAL")
    incompleteness_reason: Optional[str] = Field(None, description="Why the comparison could not be completed")


# ---------------------------------------------------------------------------
# Coverage contract
# ---------------------------------------------------------------------------

class CoverageReport(BaseModel):
    """Search coverage summary — always included, even when results are good."""

    planned_searches: int
    executed_searches: int
    failed_searches: int
    time_window_days: int
    source_types_found: list[str] = Field(default_factory=list, description="e.g. ['news', 'press_release', 'filing']")
    origin_diversity_score: float = Field(..., ge=0.0, le=1.0, description="unique independent origins / total origins")
    gaps: list[str] = Field(default_factory=list, description="Topics or questions not adequately covered")
    warnings: list[str] = Field(default_factory=list, description="e.g. 'All sources from one origin', 'Search provider timeout'")


# ---------------------------------------------------------------------------
# Stress test contracts
# ---------------------------------------------------------------------------

class StressTestPointResult(BaseModel):
    """Assessment of a single talking point against available evidence."""

    original_point: str
    extracted_claims: list[str] = Field(..., description="Atomic claims parsed from the talking point")
    assessments: list[ExtractedClaim] = Field(default_factory=list, description="Matched claims with evidence")
    suggested_wording: Optional[str] = Field(None, description="Grounded rewrite — None if evidence is insufficient")
    needs_more_research: bool = Field(False, description="True when claims could not be matched to existing evidence")


class StressTestResult(BaseModel):
    """Full stress-test output for all submitted talking points."""

    points: list[StressTestPointResult]


# ---------------------------------------------------------------------------
# Instrumentation and Usage Contracts
# ---------------------------------------------------------------------------

class LLMUsageReport(BaseModel):
    """Summarized LLM usage metrics for auditability, telemetry, and quota management."""

    total_requests: int = Field(0, description="Total physical network requests sent to LLM provider")
    total_input_tokens: int = Field(0, description="Estimated or reported input prompt tokens")
    total_output_tokens: int = Field(0, description="Estimated or reported output completion tokens")
    cache_hits: int = Field(0, description="Number of requests resolved from local content cache")
    cache_misses: int = Field(0, description="Number of requests that required model execution")
    retries: int = Field(0, description="Number of retry attempts due to transient errors or rate limits")
    stages: dict[str, int] = Field(default_factory=dict, description="Request count broken down by pipeline stage")


# ---------------------------------------------------------------------------
# Top-level engine output
# ---------------------------------------------------------------------------

class IntelligenceResult(BaseModel):
    """Complete typed output returned by run_intelligence_engine() to the backend worker."""

    session_id: str
    job_id: str
    status: str = Field(..., description="EngineResultStatus constant: COMPLETED | PARTIAL | FAILED")

    briefing_summary: Optional[str] = Field(None, description="Executive synthesized research briefing")
    sources: list[SourceRecord] = Field(default_factory=list)
    origins: list[SourceOriginRecord] = Field(default_factory=list)
    events: list[ExtractedEvent] = Field(default_factory=list)
    event_versions: list[EventVersionRecord] = Field(default_factory=list)
    claims: list[ExtractedClaim] = Field(default_factory=list)

    coverage: CoverageReport
    delta: Optional[DeltaRecord] = Field(None, description="None when no baseline was supplied")
    stress_test: Optional[StressTestResult] = Field(None, description="None when no talking points were submitted")

    warnings: list[str] = Field(default_factory=list, description="Non-fatal issues encountered during the run")
    provider_metadata: dict = Field(default_factory=dict, description="Model name, search provider, run timestamp — for reproducibility")
    llm_usage: Optional[LLMUsageReport] = Field(None, description="Centralized LLM telemetry and quota usage report")
