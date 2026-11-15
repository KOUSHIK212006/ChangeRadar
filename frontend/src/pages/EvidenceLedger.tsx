import React, { useState } from 'react';
import { useSessions } from '../hooks/useResearch';
import { PageHeader } from '../components/common/PageHeader';
import { ClaimTable } from '../components/research/ClaimTable';
import { Loader } from '../components/common/Loader';
import { ErrorState } from '../components/common/ErrorState';
import { ExtractedClaim, SourceRecord } from '../types/research';
import { ShieldCheck } from 'lucide-react';

export const EvidenceLedger: React.FC = () => {
  const { data: sessions, isLoading, error, refetch } = useSessions();
  const [selectedSessionId, setSelectedSessionId] = useState<string>('ALL');

  if (isLoading) {
    return <Loader label="Loading global evidence ledger..." size="lg" />;
  }

  if (error || !sessions) {
    return (
      <ErrorState
        title="Failed to Load Evidence Ledger"
        message={(error as Error)?.message}
        onRetry={() => refetch()}
      />
    );
  }

  // Aggregate claims and sources
  const activeSessions =
    selectedSessionId === 'ALL'
      ? sessions
      : sessions.filter((s) => s.id === selectedSessionId);

  const allClaims: ExtractedClaim[] = activeSessions.flatMap(
    (s) => s.latest_result?.claims || []
  );

  const allSources: SourceRecord[] = activeSessions.flatMap(
    (s) => s.latest_result?.sources || []
  );

  return (
    <div className="space-y-6 animate-fadeIn">
      <PageHeader
        title="Evidence Ledger & Verification Engine"
        subtitle="Granular repository of atomic propositions extracted from primary sources, audited for editorial independence, and classified by evidence stance."
        breadcrumbs={[
          { label: 'Overview', href: '/' },
          { label: 'Evidence Ledger' },
        ]}
        actions={
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-text-muted">SESSION:</span>
            <select
              value={selectedSessionId}
              onChange={(e) => setSelectedSessionId(e.target.value)}
              className="radar-input text-xs font-mono py-1.5"
            >
              <option value="ALL">All Active Sessions ({sessions.length})</option>
              {sessions.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.target_name}
                </option>
              ))}
            </select>
          </div>
        }
      />

      {/* Summary Banner */}
      <div className="radar-card p-5 bg-bg-elevated/40 border border-border flex items-center justify-between flex-wrap gap-4 text-xs font-mono">
        <div className="flex items-center gap-3">
          <ShieldCheck className="w-4 h-4 text-accent" />
          <span className="text-text-primary">
            Tracing {allClaims.length} Claims across {allSources.length} Primary Source Documents
          </span>
        </div>
        <span className="text-text-muted">
          Principle: Syndication Count ≠ Independent Corroboration
        </span>
      </div>

      <ClaimTable claims={allClaims} sources={allSources} />
    </div>
  );
};

