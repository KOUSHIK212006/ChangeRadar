import { describe, it, expect, beforeEach } from 'vitest';
import { researchService } from '../services/researchService';
import { setMockMode } from '../services/api';

describe('researchService', () => {
  beforeEach(() => {
    setMockMode(true);
  });

  it('retrieves active research sessions', async () => {
    const sessions = await researchService.getSessions();
    expect(sessions).toBeDefined();
    expect(sessions.length).toBeGreaterThan(0);
    expect(sessions[0]).toHaveProperty('target_name');
    expect(sessions[0]).toHaveProperty('scope');
  });

  it('filters sessions by scope', async () => {
    const personalSessions = await researchService.getSessions('PERSONAL');
    personalSessions.forEach((s) => {
      expect(s.scope).toBe('PERSONAL');
    });

    const workspaceSessions = await researchService.getSessions('WORKSPACE');
    workspaceSessions.forEach((s) => {
      expect(s.scope).toBe('WORKSPACE');
    });
  });

  it('retrieves a single session with intelligence result', async () => {
    const session = await researchService.getSession('sess-001');
    expect(session.id).toBe('sess-001');
    expect(session.target_name).toBe('Acme Corp');
    expect(session.latest_result).toBeDefined();
    expect(session.latest_result?.events.length).toBeGreaterThan(0);
    expect(session.latest_result?.claims.length).toBeGreaterThan(0);
  });

  it('creates a new research session and schedules job', async () => {
    const newSession = await researchService.createSession({
      target_name: 'Test Target Corp',
      target_type: 'company',
      meeting_context: 'Testing pipeline execution',
      time_window_days: 14,
      scope: 'PERSONAL',
      research_questions: ['What is their latest patent?'],
      talking_points: ['They lead the market.'],
    });

    expect(newSession.id).toBeDefined();
    expect(newSession.target_name).toBe('Test Target Corp');
    expect(newSession.latest_job).toBeDefined();
    expect(newSession.latest_job?.status).toBe('RUNNING');
    expect(newSession.latest_job?.current_stage).toBe('REQUEST_ACCEPTED');
  });

  it('marks a session as reviewed and establishes a baseline timestamp', async () => {
    const result = await researchService.markReviewed('sess-001');
    expect(result.success).toBe(true);
    expect(result.reviewed_at).toBeDefined();

    const updated = await researchService.getSession('sess-001');
    expect(updated.last_reviewed_at).toBe(result.reviewed_at);
  });

  it('stress-tests talking points and returns evidence-grounded revisions', async () => {
    const testResult = await researchService.submitStressTest('sess-001', {
      talking_points: [
        'Acme Corp revenue grew 20% in Q3',
        'Acme has named a permanent CFO successor',
      ],
    });

    expect(testResult.points).toHaveLength(2);
    // Point 1 should catch the 20% growth contradiction (actual was 14%)
    expect(testResult.points[0].assessments[0].assessment).toBe('CONTRADICTED');
    expect(testResult.points[0].suggested_wording).toBeDefined();

    // Point 2 should note insufficient/interim evidence
    expect(testResult.points[1].assessments[0].assessment).toBe('INSUFFICIENT');
    expect(testResult.points[1].needs_more_research).toBe(true);
  });
});

