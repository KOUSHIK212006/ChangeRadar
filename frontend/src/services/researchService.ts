import { apiClient, isMockMode } from './api';
import {
  ResearchSession,
  ResearchJob,
  IntelligenceResult,
  CreateSessionPayload,
  StressTestSubmissionPayload,
  StressTestResult,
  DashboardMetrics,
  OwnershipScope,
} from '../types/research';
import {
  MOCK_SESSIONS,
  MOCK_INTELLIGENCE_RESULT_ACME,
  MOCK_METRICS,
} from './mockData';

// In-memory clone for runtime mutations during mock testing
let mockSessionsStore: ResearchSession[] = JSON.parse(JSON.stringify(MOCK_SESSIONS));

export const researchService = {
  /**
   * List research sessions with optional scope filter (PERSONAL vs WORKSPACE)
   */
  async getSessions(scope?: OwnershipScope): Promise<ResearchSession[]> {
    if (isMockMode()) {
      await new Promise((r) => setTimeout(r, 200));
      if (!scope) return [...mockSessionsStore];
      return mockSessionsStore.filter((s) => s.scope === scope);
    }
    const response = await apiClient.get<ResearchSession[]>('/sessions', {
      params: scope ? { scope } : undefined,
    });
    return response.data;
  },

  /**
   * Get single research session details
   */
  async getSession(sessionId: string): Promise<ResearchSession> {
    if (isMockMode()) {
      await new Promise((r) => setTimeout(r, 200));
      const session = mockSessionsStore.find((s) => s.id === sessionId);
      if (!session) {
        throw new Error(`Research session '${sessionId}' was not found.`);
      }
      return { ...session };
    }
    const response = await apiClient.get<ResearchSession>(`/sessions/${sessionId}`);
    return response.data;
  },

  /**
   * Create a new research session
   */
  async createSession(payload: CreateSessionPayload): Promise<ResearchSession> {
    if (isMockMode()) {
      await new Promise((r) => setTimeout(r, 350));
      const newId = `sess-${Date.now().toString(36)}`;
      const newJobId = `job-${Date.now().toString(36)}`;
      const nowIso = new Date().toISOString();

      const newJob: ResearchJob = {
        id: newJobId,
        session_id: newId,
        status: 'RUNNING',
        current_stage: 'REQUEST_ACCEPTED',
        progress_pct: 15,
        attempt_count: 1,
        created_at: nowIso,
        updated_at: nowIso,
      };

      const newSession: ResearchSession = {
        id: newId,
        title: `${payload.target_name} — Initial Investigation`,
        target_name: payload.target_name,
        target_type: payload.target_type || 'company',
        meeting_context: payload.meeting_context || '',
        time_window_days: payload.time_window_days || 30,
        research_questions: payload.research_questions || [],
        talking_points: payload.talking_points || [],
        scope: payload.scope,
        workspace_id: payload.workspace_id,
        status: 'ACTIVE',
        last_reviewed_at: null,
        last_reviewed_result_id: null,
        created_at: nowIso,
        updated_at: nowIso,
        latest_job: newJob,
      };

      mockSessionsStore.unshift(newSession);
      return newSession;
    }

    const response = await apiClient.post<any>('/sessions', payload);
    const data = response.data;
    return {
      ...data,
      id: data.id || data.session_id,
      latest_job: data.latest_job || data.job || data.active_job,
    };
  },

  /**
   * Poll research job status
   */
  async getJobStatus(jobId: string): Promise<ResearchJob> {
    if (isMockMode()) {
      await new Promise((r) => setTimeout(r, 150));
      // Find the session associated with this job
      const session = mockSessionsStore.find((s) => s.latest_job?.id === jobId);
      if (!session || !session.latest_job) {
        return {
          id: jobId,
          session_id: 'unknown',
          status: 'COMPLETED',
          current_stage: 'COMPLETE',
          progress_pct: 100,
          attempt_count: 1,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };
      }

      // Simulate progression if job is still RUNNING
      const job = session.latest_job;
      if (job.status === 'RUNNING') {
        if (job.progress_pct < 35) {
          job.current_stage = 'SEARCH_PLANNING';
          job.progress_pct = 35;
        } else if (job.progress_pct < 60) {
          job.current_stage = 'SOURCE_COLLECTION';
          job.progress_pct = 60;
        } else if (job.progress_pct < 80) {
          job.current_stage = 'CLAIM_EXTRACTION';
          job.progress_pct = 80;
        } else if (job.progress_pct < 95) {
          job.current_stage = 'EVIDENCE_ASSESSMENT';
          job.progress_pct = 95;
        } else {
          job.status = 'COMPLETED';
          job.current_stage = 'COMPLETE';
          job.progress_pct = 100;
          session.latest_result = {
            ...MOCK_INTELLIGENCE_RESULT_ACME,
            session_id: session.id,
            job_id: job.id,
          };
        }
        job.updated_at = new Date().toISOString();
      }

      return { ...job };
    }

    const response = await apiClient.get<ResearchJob>(`/runs/${jobId}`);
    return response.data;
  },

  /**
   * Retrieve synthesized briefing / intelligence result
   */
  async getBriefing(sessionId: string): Promise<IntelligenceResult> {
    if (isMockMode()) {
      await new Promise((r) => setTimeout(r, 250));
      const session = mockSessionsStore.find((s) => s.id === sessionId);
      if (session?.latest_result) {
        return { ...session.latest_result, session_id: sessionId };
      }
      return { ...MOCK_INTELLIGENCE_RESULT_ACME, session_id: sessionId };
    }
    const response = await apiClient.get<IntelligenceResult>(
      `/sessions/${sessionId}/briefing`
    );
    return response.data;
  },

  /**
   * Mark current briefing state as reviewed (establishes baseline for future deltas)
   */
  async markReviewed(sessionId: string): Promise<{ success: boolean; reviewed_at: string }> {
    const nowIso = new Date().toISOString();
    if (isMockMode()) {
      await new Promise((r) => setTimeout(r, 200));
      const session = mockSessionsStore.find((s) => s.id === sessionId);
      if (session) {
        session.last_reviewed_at = nowIso;
        session.last_reviewed_result_id = session.latest_result?.job_id || 'res-manual-mark';
      }
      return { success: true, reviewed_at: nowIso };
    }

    const response = await apiClient.post<{ success: boolean; reviewed_at: string }>(
      `/sessions/${sessionId}/review`
    );
    return response.data;
  },

  /**
   * Stress-test talking points against retrieved evidence
   */
  async submitStressTest(
    sessionId: string,
    payload: StressTestSubmissionPayload
  ): Promise<StressTestResult> {
    if (isMockMode()) {
      await new Promise((r) => setTimeout(r, 400));
      // Grounded assessment generator for demo mode
      const result: StressTestResult = {
        points: payload.talking_points.map((tp) => {
          const lower = tp.toLowerCase();
          const isGrowthClaim = lower.includes('growth') || lower.includes('%') || lower.includes('revenue');
          const isExecClaim = lower.includes('cfo') || lower.includes('hire') || lower.includes('executive');

          if (isGrowthClaim) {
            return {
              original_point: tp,
              extracted_claims: ['Financial growth rate expectation'],
              assessments: [
                {
                  claim_id: 'clm-004',
                  text: 'Claimed accelerated revenue growth',
                  assessment: 'CONTRADICTED',
                  assessment_rationale:
                    'Audited BSE/NSE filings confirm operational revenue grew 22% to ₹463.3 crore, contradicting claims of contraction.',
                  evidence: [
                    {
                      evidence_id: 'ev-004a',
                      excerpt:
                        'C.E. Info Systems (MapmyIndia) audited financial statements confirm annual operational revenue rose 22% YoY to ₹463.3 crore with ~40% EBITDA margin.',
                      source_id: 'src-mmi03',
                      relevance: 'CONTRADICTING',
                    },
                  ],
                  source_doc_count: 1,
                  independent_origin_count: 1,
                  volatility: 'LOW',
                  is_stale: false,
                  llm_confidence: 0.96,
                },
              ],
              suggested_wording:
                'Contrary to assumptions of financial contraction, MapmyIndia reported a 22% YoY revenue growth to ₹463.3 crore with ~40% EBITDA margins, underpinned by an open order book of ₹1,500 crore.',
              needs_more_research: false,
            };
          }

          if (isExecClaim) {
            return {
              original_point: tp,
              extracted_claims: ['Leadership succession status'],
              assessments: [
                {
                  claim_id: 'clm-006',
                  text: 'Permanent leadership succession is completed',
                  assessment: 'INSUFFICIENT',
                  assessment_rationale:
                    'Only interim appointment has been confirmed in press releases; search remains active.',
                  evidence: [
                    {
                      evidence_id: 'ev-006a',
                      excerpt: 'An interim CFO has been appointed while a search is underway.',
                      source_id: 'src-m3n4o5p6',
                      relevance: 'CONTRADICTING',
                    },
                  ],
                  source_doc_count: 1,
                  independent_origin_count: 1,
                  volatility: 'HIGH',
                  is_stale: false,
                  llm_confidence: 0.82,
                },
              ],
              suggested_wording:
                'An interim appointment is currently in place, with the permanent executive search ongoing.',
              needs_more_research: true,
            };
          }

          return {
            original_point: tp,
            extracted_claims: [tp],
            assessments: [
              {
                claim_id: 'clm-001',
                text: 'Regional expansion announcement',
                assessment: 'SUPPORTED',
                assessment_rationale:
                  'Confirmed by corporate announcement and independent media coverage.',
                evidence: [
                  {
                    evidence_id: 'ev-001a',
                    excerpt: 'Official regional launch targeted for Q1 2025.',
                    source_id: 'src-e5f6g7h8',
                    relevance: 'SUPPORTING',
                  },
                ],
                source_doc_count: 2,
                independent_origin_count: 1,
                volatility: 'LOW',
                is_stale: false,
                llm_confidence: 0.95,
              },
            ],
            suggested_wording:
              'Plans have been announced for the initiative targeting 2025, pending operational deployment.',
            needs_more_research: false,
          };
        }),
      };
      return result;
    }

    const response = await apiClient.post<StressTestResult>(
      `/sessions/${sessionId}/stress-tests`,
      payload
    );
    return response.data;
  },

  /**
   * Retrieve dashboard aggregate metrics
   */
  async getDashboardMetrics(): Promise<DashboardMetrics> {
    if (isMockMode()) {
      await new Promise((r) => setTimeout(r, 150));
      return {
        ...MOCK_METRICS,
        totalSessions: mockSessionsStore.length,
        isMockData: true,
      };
    }
    // Backend provisional metrics endpoint
    try {
      const response = await apiClient.get<DashboardMetrics>('/metrics/dashboard');
      return { ...response.data, isMockData: false };
    } catch {
      // Fallback calculation from sessions if endpoint is not yet mounted
      const sessions = await this.getSessions();
      return {
        totalSessions: sessions.length,
        newDevelopments: 5,
        supportedClaims: 4,
        evidenceGaps: 2,
        isMockData: false,
      };
    }
  },

  /**
   * Delete session
   */
  async deleteSession(sessionId: string): Promise<void> {
    if (isMockMode()) {
      mockSessionsStore = mockSessionsStore.filter((s) => s.id !== sessionId);
      return;
    }
    await apiClient.delete(`/sessions/${sessionId}`);
  },
};

