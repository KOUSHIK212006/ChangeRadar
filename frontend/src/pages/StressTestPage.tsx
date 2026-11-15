import React, { useState } from 'react';
import { useSessions } from '../hooks/useResearch';
import { PageHeader } from '../components/common/PageHeader';
import { TalkingPointTester } from '../components/research/TalkingPointTester';
import { Loader } from '../components/common/Loader';
import { ErrorState } from '../components/common/ErrorState';

export const StressTestPage: React.FC = () => {
  const { data: sessions, isLoading, error, refetch } = useSessions();
  const [selectedSessionId, setSelectedSessionId] = useState<string>('');

  if (isLoading) {
    return <Loader label="Loading session targets for stress test..." size="lg" />;
  }

  if (error || !sessions || sessions.length === 0) {
    return (
      <ErrorState
        title="No Research Target Available"
        message="Please launch at least one research session to stress-test your meeting talking points against verified evidence."
        onRetry={() => refetch()}
      />
    );
  }

  const activeSessionId = selectedSessionId || sessions[0].id;
  const currentSession = sessions.find((s) => s.id === activeSessionId) || sessions[0];

  return (
    <div className="space-y-6 animate-fadeIn max-w-5xl mx-auto">
      <PageHeader
        title="Talking-Point Stress Test"
        subtitle="Submit proposed statements and questions before critical meetings. ChangeRadar checks them against primary evidence to catch contradictions and suggest defensible alternatives."
        breadcrumbs={[
          { label: 'Overview', href: '/' },
          { label: 'Stress Test' },
        ]}
        actions={
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-text-muted">TARGET:</span>
            <select
              value={activeSessionId}
              onChange={(e) => setSelectedSessionId(e.target.value)}
              className="radar-input text-xs font-mono py-1.5"
            >
              {sessions.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.target_name} ({s.scope})
                </option>
              ))}
            </select>
          </div>
        }
      />

      <TalkingPointTester
        sessionId={currentSession.id}
        initialResults={currentSession.latest_result?.stress_test}
      />
    </div>
  );
};

