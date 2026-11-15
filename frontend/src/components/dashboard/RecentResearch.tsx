import React from 'react';
import { Link } from 'react-router-dom';
import { ResearchSession } from '../../types/research';
import { Badge } from '../common/Badge';
import { ArrowUpRight, Clock } from 'lucide-react';

interface RecentResearchProps {
  sessions: ResearchSession[];
  isLoading?: boolean;
}

export const RecentResearch: React.FC<RecentResearchProps> = ({
  sessions,
  isLoading,
}) => {
  if (isLoading) {
    return (
      <div className="radar-card p-6 space-y-4">
        <div className="h-5 bg-bg-elevated rounded w-1/4 animate-pulse"></div>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-16 bg-bg-elevated rounded-lg animate-pulse"
            ></div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="radar-card p-6">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h2 className="font-heading font-semibold text-lg text-text-primary">
            Recent Research Sessions
          </h2>
          <p className="text-xs text-text-secondary">
            Target entities tracked against review baselines
          </p>
        </div>
        <Link
          to="/history"
          className="text-xs font-mono text-accent hover:text-accent-hover flex items-center gap-1 transition-colors"
        >
          <span>View All</span>
          <ArrowUpRight className="w-3.5 h-3.5" />
        </Link>
      </div>

      {sessions.length === 0 ? (
        <div className="text-center py-8 text-text-secondary text-sm">
          No research sessions active. Start your first investigation above.
        </div>
      ) : (
        <div className="divide-y divide-border/60">
          {sessions.slice(0, 5).map((session) => {
            const jobStatus = session.latest_job?.status || 'COMPLETED';
            const updatedDate = new Date(session.updated_at).toLocaleDateString(
              undefined,
              {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
              }
            );

            return (
              <div
                key={session.id}
                className="py-3.5 first:pt-0 last:pb-0 flex flex-col sm:flex-row sm:items-center justify-between gap-3 group"
              >
                <div className="space-y-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <Link
                      to={`/research/${session.id}`}
                      className="font-medium text-sm text-text-primary group-hover:text-accent transition-colors truncate"
                    >
                      {session.target_name}
                    </Link>
                    <Badge type="scope" value={session.scope} size="sm" />
                    <Badge type="job" value={jobStatus} size="sm" />
                  </div>
                  {session.meeting_context && (
                    <p className="text-xs text-text-secondary truncate max-w-md">
                      {session.meeting_context}
                    </p>
                  )}
                </div>

                <div className="flex items-center gap-4 text-xs font-mono text-text-muted shrink-0">
                  <span className="flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5" />
                    <span>{updatedDate}</span>
                  </span>
                  <Link
                    to={`/research/${session.id}`}
                    className="radar-button-secondary text-xs py-1 px-2.5"
                  >
                    <span>Inspect</span>
                    <ArrowUpRight className="w-3 h-3 text-accent" />
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

