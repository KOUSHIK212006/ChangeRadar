/**
 * ChangeRadar Shared Contracts & Frontend Typed Models
 * Aligned with:
 * - Intelligence Engine (Surjith): contracts.py & sample_result.json
 * - Platform & Backend (Krishank): models/enums.py & research_session.py
 */

export type OwnershipScope = 'PERSONAL' | 'WORKSPACE';

export type SessionStatus = 'ACTIVE' | 'ARCHIVED';

export type ResearchJobStatus =
  | 'QUEUED'
  | 'RUNNING'
  | 'RETRY_WAIT'
  | 'COMPLETED'
  | 'PARTIAL'
  | 'FAILED'
  | 'CANCELLED';

export type EvidenceVerificationStatus =
  | 'SUPPORTED'
  | 'PARTIALLY_SUPPORTED'
  | 'CONTRADICTED'
  | 'INSUFFICIENT'
  | 'OUTDATED'
  | 'UNVERIFIABLE';

export type EventLifecycle = 'NEW' | 'DEVELOPING' | 'UPDATED' | 'COMPLETED';

export type ClaimVolatility = 'LOW' | 'MEDIUM' | 'HIGH';

export type EvidenceStance = 'SUPPORTING' | 'CONTRADICTING' | 'CONTEXTUAL';

export interface SourceRecord {
  source_id: string; // sha256(canonical_url)[:16]
  url: string;
  canonical_url: string;
  title: string;
  publisher: string;
  snippet: string;
  published_at?: string | null; // ISO 8601 UTC
  discovered_at: string; // ISO 8601 UTC
  is_syndicated: boolean;
  syndication_confidence: number;
}

export interface SourceOriginRecord {
  origin_id: string;
  label: string;
  source_ids: string[];
  is_independent: boolean;
  independence_confidence: number;
}

export interface EvidenceRecord {
  evidence_id: string;
  excerpt: string;
  source_id: string;
  relevance: EvidenceStance;
}

export interface ExtractedClaim {
  claim_id: string;
  text: string;
  assessment: EvidenceVerificationStatus;
  assessment_rationale: string;
  evidence: EvidenceRecord[];
  source_doc_count: number;
  independent_origin_count: number;
  volatility: ClaimVolatility;
  is_stale: boolean;
  llm_confidence: number; // 0.0 - 1.0 (internal diagnostic, not proof)
}

export interface EventVersionRecord {
  version_id: string;
  event_id: string;
  description: string;
  lifecycle_status: EventLifecycle;
  source_ids: string[];
  recorded_at: string;
}

export interface ExtractedEvent {
  event_id: string;
  title: string;
  description: string;
  lifecycle_status: EventLifecycle;
  is_disputed: boolean;
  is_uncertain: boolean;
  event_at?: string | null; // When event happened
  published_at?: string | null; // Earliest publication
  discovered_at: string; // Discovery timestamp
  source_ids: string[];
  origin_ids: string[];
  claim_ids: string[];
}

export interface CoverageReport {
  planned_searches: number;
  executed_searches: number;
  failed_searches: number;
  time_window_days: number;
  source_types_found: string[];
  origin_diversity_score: number; // 0.0 - 1.0
  gaps: string[];
  warnings: string[];
}

export interface DeltaRecord {
  new_events: string[];
  updated_events: string[];
  new_evidence_for_claims: string[];
  changed_assessments: string[];
  no_material_change: boolean;
  comparison_incomplete: boolean;
  incompleteness_reason?: string | null;
}

export interface StressTestPointResult {
  original_point: string;
  extracted_claims: string[];
  assessments: ExtractedClaim[];
  suggested_wording?: string | null;
  needs_more_research: boolean;
}

export interface StressTestResult {
  points: StressTestPointResult[];
}

export interface LLMUsageReport {
  total_requests: number;
  total_input_tokens: number;
  total_output_tokens: number;
  cache_hits: number;
  cache_misses: number;
  retries: number;
  stages: Record<string, number>;
}

export interface IntelligenceResult {
  session_id: string;
  job_id: string;
  status: 'COMPLETED' | 'PARTIAL' | 'FAILED';
  executive_summary?: string;
  briefing_summary?: string | null;
  sources: SourceRecord[];
  origins: SourceOriginRecord[];
  events: ExtractedEvent[];
  event_versions: EventVersionRecord[];
  claims: ExtractedClaim[];
  coverage: CoverageReport;
  delta?: DeltaRecord | null;
  stress_test?: StressTestResult | null;
  warnings: string[];
  provider_metadata?: Record<string, unknown>;
  llm_usage?: LLMUsageReport | null;
}

export interface ResearchJob {
  id: string;
  session_id: string;
  status: ResearchJobStatus;
  current_stage:
    | 'REQUEST_ACCEPTED'
    | 'SEARCH_PLANNING'
    | 'SOURCE_COLLECTION'
    | 'CLAIM_EXTRACTION'
    | 'EVIDENCE_ASSESSMENT'
    | 'TEMPORAL_COMPARISON'
    | 'COVERAGE_AUDIT'
    | 'BRIEFING_GENERATION'
    | 'COMPLETE';
  progress_pct: number;
  attempt_count: number;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ResearchSession {
  id: string;
  title: string;
  target_name: string;
  target_type?: string;
  meeting_context?: string;
  time_window_days: number;
  research_questions: string[];
  talking_points: string[];
  scope: OwnershipScope;
  owner_user_id?: string;
  workspace_id?: string;
  status: SessionStatus;
  last_reviewed_at?: string | null;
  last_reviewed_result_id?: string | null;
  created_at: string;
  updated_at: string;
  latest_job?: ResearchJob;
  latest_result?: IntelligenceResult;
}

export interface CreateSessionPayload {
  target_name: string;
  target_type?: string;
  meeting_context?: string;
  time_window_days?: number;
  research_questions?: string[];
  talking_points?: string[];
  scope: OwnershipScope;
  workspace_id?: string;
  baseline_session_id?: string;
}

export interface StressTestSubmissionPayload {
  talking_points: string[];
}

export interface DashboardMetrics {
  totalSessions: number;
  newDevelopments: number;
  supportedClaims: number;
  evidenceGaps: number;
  isMockData: boolean;
}

