import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useSession, useJobStatus, useBriefing } from '../hooks/useResearch';
import { PageHeader } from '../components/common/PageHeader';
import { Badge } from '../components/common/Badge';
import { Loader } from '../components/common/Loader';
import { ErrorState } from '../components/common/ErrorState';
import { ResearchProgress } from '../components/research/ResearchProgress';
import { EventTimeline } from '../components/research/EventTimeline';
import { ClaimTable } from '../components/research/ClaimTable';
import { PersonalDeltaCard } from '../components/research/PersonalDeltaCard';
import { CoverageAuditCard } from '../components/research/CoverageAuditCard';
import { TalkingPointTester } from '../components/research/TalkingPointTester';
import { EvidenceCard } from '../components/research/EvidenceCard';
import { FileText } from 'lucide-react';

type ActiveTab = 'overview' | 'timeline' | 'claims' | 'delta' | 'sources' | 'coverage' | 'stressTest';

export const ResearchDetails: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [activeTab, setActiveTab] = useState<ActiveTab>('overview');

  const {
    data: session,
    isLoading: sessionLoading,
    error: sessionError,
    refetch: refetchSession,
  } = useSession(id || '');

  const jobId = session?.latest_job?.id;
  const isJobRunning = session?.latest_job?.status === 'RUNNING';

  const { data: jobStatus } = useJobStatus(jobId, isJobRunning);
  const activeJob = jobStatus || session?.latest_job;

  const {
    data: briefing,
    refetch: refetchBriefing,
  } = useBriefing(id || '', activeJob?.status === 'COMPLETED' || activeJob?.status === 'PARTIAL');

  if (sessionLoading) {
    return <Loader label="Loading research session and context..." size="lg" />;
  }

  if (sessionError || !session) {
    return (
      <ErrorState
        title="Session Not Found"
        message={
          (sessionError as Error)?.message ||
          `The requested research session '${id}' could not be located.`
        }
        onRetry={() => refetchSession()}
      />
    );
  }

  const result = briefing || session.latest_result;

  const tabs: { key: ActiveTab; label: string; count?: number }[] = [
    { key: 'overview', label: 'Executive Briefing' },
    { key: 'timeline', label: 'Event Timeline', count: result?.events?.length },
    { key: 'claims', label: 'Claims & Evidence', count: result?.claims?.length },
    { key: 'delta', label: 'Personal Delta' },
    { key: 'sources', label: 'Sources & Origins', count: result?.sources?.length },
    { key: 'coverage', label: 'Coverage Audit' },
    { key: 'stressTest', label: 'Stress Test' },
  ];

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Page Header */}
      <PageHeader
        title={session.target_name}
        subtitle={
          session.meeting_context ||
          'Comprehensive evidence dossier and baseline delta analysis.'
        }
        breadcrumbs={[
          { label: 'Overview', href: '/' },
          { label: 'Research Sessions', href: '/history' },
          { label: session.target_name },
        ]}
        badge={
          <div className="flex items-center gap-2">
            <Badge type="scope" value={session.scope} />
            {activeJob && <Badge type="job" value={activeJob.status} />}
          </div>
        }
        actions={
          <div className="flex items-center gap-2 text-xs font-mono text-text-muted">
            <span className="hidden sm:inline">Session ID: {session.id}</span>
          </div>
        }
      />

      {/* In-Progress Pipeline Card (Visible if active) */}
      {activeJob && activeJob.status === 'RUNNING' && (
        <div className="mb-6">
          <ResearchProgress job={activeJob} onRefresh={() => refetchBriefing()} />
        </div>
      )}

      {/* Tabs Navigation */}
      <div className="border-b border-border flex items-center gap-2 overflow-x-auto no-scrollbar">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActiveTab(tab.key)}
              className={`py-3 px-3.5 text-xs md:text-sm font-medium border-b-2 transition-colors whitespace-nowrap flex items-center gap-2 ${
                isActive
                  ? 'border-accent text-accent font-semibold'
                  : 'border-transparent text-text-secondary hover:text-text-primary hover:border-border'
              }`}
            >
              <span>{tab.label}</span>
              {typeof tab.count === 'number' && (
                <span
                  className={`text-[10px] font-mono px-1.5 py-0.2 rounded ${
                    isActive
                      ? 'bg-accent/20 text-accent'
                      : 'bg-bg-elevated text-text-muted'
                  }`}
                >
                  {tab.count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      <div className="pt-2">
        {/* TAB 1: EXECUTIVE BRIEFING OVERVIEW */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* Executive Summary Card */}
            <div className="radar-card p-6 md:p-8 space-y-4">
              <div className="flex items-center justify-between border-b border-border/60 pb-4">
                <div className="flex items-center gap-2 text-xs font-mono uppercase text-accent font-semibold tracking-wider">
                  <FileText className="w-4 h-4" />
                  <span>Synthesized Executive Briefing</span>
                </div>
                <div className="text-[11px] font-mono text-text-muted">
                  Window: Past {session.time_window_days} Days
                </div>
              </div>

              <p className="text-sm md:text-base text-text-primary leading-relaxed font-sans font-normal">
                {result?.executive_summary ||
                  'Intelligence extraction complete. Key events and verified atomic claims have been compiled below from primary sources.'}
              </p>

              {/* Research Questions & Answers */}
              {session.research_questions && session.research_questions.length > 0 && (
                <div className="pt-4 border-t border-border/40 space-y-3">
                  <h4 className="text-xs font-mono uppercase tracking-wider text-text-muted">
                    Investigated Questions:
                  </h4>
                  <div className="space-y-2">
                    {session.research_questions.map((q, idx) => (
                      <div
                        key={idx}
                        className="p-3 rounded-lg bg-bg-elevated/40 border border-border text-xs flex items-start gap-2"
                      >
                        <span className="text-accent font-mono font-bold">Q{idx + 1}:</span>
                        <span className="text-text-primary font-medium">{q}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Quick Signals Summary Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Personal Delta Card Preview */}
              <PersonalDeltaCard
                sessionId={session.id}
                delta={result?.delta}
                lastReviewedAt={session.last_reviewed_at}
                events={result?.events || []}
                claims={result?.claims || []}
              />

              {/* Coverage Snapshot Card */}
              {result?.coverage && (
                <CoverageAuditCard coverage={result.coverage} />
              )}
            </div>
          </div>
        )}

        {/* TAB 2: EVENT TIMELINE */}
        {activeTab === 'timeline' && (
          <EventTimeline
            events={result?.events || []}
            eventVersions={result?.event_versions || []}
            sources={result?.sources || []}
            origins={result?.origins || []}
          />
        )}

        {/* TAB 3: CLAIMS & EVIDENCE LEDGER */}
        {activeTab === 'claims' && (
          <ClaimTable
            claims={result?.claims || []}
            sources={result?.sources || []}
          />
        )}

        {/* TAB 4: PERSONAL DELTA */}
        {activeTab === 'delta' && (
          <PersonalDeltaCard
            sessionId={session.id}
            delta={result?.delta}
            lastReviewedAt={session.last_reviewed_at}
            events={result?.events || []}
            claims={result?.claims || []}
          />
        )}

        {/* TAB 5: SOURCES & ORIGINS */}
        {activeTab === 'sources' && (
          <div className="space-y-6">
            <div className="border-b border-border/60 pb-3 flex items-center justify-between">
              <div>
                <h3 className="font-heading font-semibold text-lg text-text-primary">
                  Retrieved Primary Sources & Origin Clusters
                </h3>
                <p className="text-xs text-text-secondary">
                  Distinguishing individual syndicated documents from canonical editorial origins
                </p>
              </div>
              <span className="text-xs font-mono text-text-muted bg-bg-elevated px-2.5 py-1 rounded border border-border">
                {result?.sources?.length || 0} SOURCES • {result?.origins?.length || 0} ORIGINS
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {(result?.sources || []).map((src) => {
                const matchedOrigin = (result?.origins || []).find((o) =>
                  o.source_ids.includes(src.source_id)
                );
                return (
                  <EvidenceCard
                    key={src.source_id}
                    source={src}
                    origin={matchedOrigin}
                  />
                );
              })}
            </div>
          </div>
        )}

        {/* TAB 6: COVERAGE AUDIT */}
        {activeTab === 'coverage' && result?.coverage && (
          <CoverageAuditCard coverage={result.coverage} />
        )}

        {/* TAB 7: STRESS TEST */}
        {activeTab === 'stressTest' && (
          <TalkingPointTester
            sessionId={session.id}
            initialResults={result?.stress_test}
          />
        )}
      </div>
    </div>
  );
};

