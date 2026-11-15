import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useSessions, useDashboardMetrics } from '../hooks/useResearch';
import { StatsCard } from '../components/dashboard/StatsCard';
import { RecentResearch } from '../components/dashboard/RecentResearch';
import { ActivityFeed } from '../components/dashboard/ActivityFeed';
import { ErrorState } from '../components/common/ErrorState';
import {
  Radar,
  Plus,
  Sparkles,
  ShieldCheck,
  AlertTriangle,
  FolderOpen,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const { data: sessions, isLoading: sessionsLoading, error: sessionsError, refetch: refetchSessions } =
    useSessions();
  const { data: metrics, error: metricsError, refetch: refetchMetrics } =
    useDashboardMetrics();

  const handleRetry = () => {
    refetchSessions();
    refetchMetrics();
  };

  if (sessionsError || metricsError) {
    return (
      <ErrorState
        title="Failed to Load Dashboard Intelligence"
        message={
          (sessionsError as Error)?.message ||
          (metricsError as Error)?.message ||
          'Could not retrieve research sessions.'
        }
        onRetry={handleRetry}
      />
    );
  }

  // Aggregate recent events across sessions for activity feed
  const recentEvents = (sessions || []).flatMap((s) =>
    (s.latest_result?.events || []).map((e) => ({
      ...e,
      sessionTitle: s.title,
      sessionId: s.id,
    }))
  );

  // Evidence distribution data for chart
  const claimsChartData = [
    { name: 'Supported', count: 4, color: '#65B891' },
    { name: 'Partially Supp.', count: 2, color: '#E5B45C' },
    { name: 'Contradicted', count: 2, color: '#E45B3F' },
    { name: 'Insufficient', count: 2, color: '#A6A096' },
  ];

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Welcome Banner */}
      <div className="radar-card p-6 md:p-8 relative overflow-hidden bg-gradient-to-r from-bg-secondary via-bg-secondary to-bg-elevated border-border">
        <div className="relative z-10 max-w-3xl space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-accent/10 border border-accent/30 text-accent text-xs font-mono">
            <Radar className="w-3.5 h-3.5" />
            <span>CHANGE-AWARE INTELLIGENCE PLATFORM</span>
          </div>

          <h1 className="font-heading font-bold text-2xl md:text-4xl text-text-primary tracking-tight">
            Know what changed. Understand what matters. Decide what to do.
          </h1>

          <p className="text-sm md:text-base text-text-secondary leading-relaxed">
            ChangeRadar connects claims to verified evidence, separates syndication from independent origins, and stress-tests your talking points against review baselines.
          </p>

          <div className="pt-2 flex items-center gap-3 flex-wrap">
            <button
              type="button"
              onClick={() => navigate('/new')}
              className="radar-button-primary text-sm py-2.5 px-4 shadow-lg shadow-accent/10"
            >
              <Plus className="w-4 h-4" />
              <span>Start New Research</span>
            </button>
            <button
              type="button"
              onClick={() => navigate('/history')}
              className="radar-button-secondary text-sm py-2.5 px-4"
            >
              <FolderOpen className="w-4 h-4 text-text-muted" />
              <span>Browse History</span>
            </button>
          </div>
        </div>

        {/* Subtle Decorative Grid Pattern */}
        <div
          className="absolute -right-12 -bottom-12 w-64 h-64 rounded-full bg-accent/5 blur-3xl pointer-events-none"
          aria-hidden="true"
        />
      </div>

      {/* Summary Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard
          label="Research Sessions"
          value={metrics?.totalSessions ?? (sessions?.length || 0)}
          helperText="Active entities being tracked"
          icon={FolderOpen}
          variant="default"
        />
        <StatsCard
          label="Newly Detected Developments"
          value={metrics?.newDevelopments ?? 5}
          helperText="Events occurring after baseline"
          icon={Sparkles}
          variant="accent"
        />
        <StatsCard
          label="Supported Claims"
          value={metrics?.supportedClaims ?? 4}
          helperText="Corroborated by primary evidence"
          icon={ShieldCheck}
          variant="success"
        />
        <StatsCard
          label="Evidence Gaps"
          value={metrics?.evidenceGaps ?? 3}
          helperText="Unanswered angles requiring diligence"
          icon={AlertTriangle}
          variant="warning"
        />
      </div>

      {/* Analytical Overview & Distribution Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Sessions List */}
        <div className="lg:col-span-2">
          <RecentResearch
            sessions={sessions || []}
            isLoading={sessionsLoading}
          />
        </div>

        {/* Evidence Verification Health Chart */}
        <div className="radar-card p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <h2 className="font-heading font-semibold text-base text-text-primary">
                Evidence Status Breakdown
              </h2>
              <span className="text-[10px] font-mono text-text-muted bg-bg-elevated px-2 py-0.5 rounded border border-border">
                ALL CLAIMS
              </span>
            </div>
            <p className="text-xs text-text-secondary leading-relaxed mb-4">
              Distribution of claims across supported, contradicted, and insufficient evidence categories.
            </p>
          </div>

          <div className="h-44 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={claimsChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <XAxis
                  dataKey="name"
                  stroke="#77736B"
                  fontSize={10}
                  tickLine={false}
                  axisLine={{ stroke: '#393632' }}
                />
                <YAxis
                  stroke="#77736B"
                  fontSize={10}
                  tickLine={false}
                  axisLine={{ stroke: '#393632' }}
                  allowDecimals={false}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#242321',
                    borderColor: '#393632',
                    borderRadius: '8px',
                    fontSize: '11px',
                    color: '#F1EDE5',
                  }}
                  itemStyle={{ color: '#F1EDE5' }}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {claimsChartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="pt-3 border-t border-border/40 text-[11px] font-mono text-text-muted flex items-center justify-between">
            <span>Contradicted claims: Flagged</span>
            <span className="text-status-danger font-medium">2 Urgent</span>
          </div>
        </div>
      </div>

      {/* Intelligence Activity Feed */}
      <div>
        <ActivityFeed
          events={recentEvents}
          isLoading={sessionsLoading}
        />
      </div>
    </div>
  );
};

