import React from 'react';
import { Link } from 'react-router-dom';
import { ExtractedEvent } from '../../types/research';
import { Badge } from '../common/Badge';
import { Calendar, Globe2, ArrowRight } from 'lucide-react';

interface ActivityFeedProps {
  events: (ExtractedEvent & { sessionTitle?: string; sessionId?: string })[];
  isLoading?: boolean;
}

export const ActivityFeed: React.FC<ActivityFeedProps> = ({
  events,
  isLoading,
}) => {
  if (isLoading) {
    return (
      <div className="radar-card p-6 space-y-4">
        <div className="h-5 bg-bg-elevated rounded w-1/3 animate-pulse"></div>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-20 bg-bg-elevated rounded-lg animate-pulse"
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
            Recent Intelligence Signals
          </h2>
          <p className="text-xs text-text-secondary">
            Verified events and temporal shifts extracted from primary sources
          </p>
        </div>
        <span className="text-xs font-mono text-text-muted bg-bg-elevated px-2 py-0.5 rounded border border-border">
          {events.length} SIGNALS
        </span>
      </div>

      {events.length === 0 ? (
        <div className="text-center py-8 text-text-secondary text-sm">
          No recent signals detected across your review baseline.
        </div>
      ) : (
        <div className="space-y-3">
          {events.map((evt) => {
            const eventDateFormatted = evt.event_at
              ? new Date(evt.event_at).toLocaleDateString(undefined, {
                  month: 'short',
                  day: 'numeric',
                  year: 'numeric',
                })
              : 'Unknown Date';

            const discoveredFormatted = new Date(
              evt.discovered_at
            ).toLocaleDateString(undefined, {
              month: 'short',
              day: 'numeric',
            });

            return (
              <div
                key={evt.event_id}
                className="p-4 rounded-xl bg-bg-elevated/50 border border-border/70 hover:border-border transition-colors space-y-2"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2 flex-wrap">
                    <Badge type="lifecycle" value={evt.lifecycle_status} size="sm" />
                    {evt.is_disputed && (
                      <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-status-danger/15 text-status-danger border border-status-danger/30">
                        Disputed Event
                      </span>
                    )}
                    {evt.is_uncertain && (
                      <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-status-warning/15 text-status-warning border border-status-warning/30">
                        Uncertain Precision
                      </span>
                    )}
                  </div>
                  <div className="text-[11px] font-mono text-text-muted shrink-0 flex items-center gap-1.5">
                    <Calendar className="w-3 h-3 text-accent" />
                    <span>Occurred: {eventDateFormatted}</span>
                  </div>
                </div>

                <h4 className="font-medium text-sm text-text-primary leading-snug">
                  {evt.title}
                </h4>

                <p className="text-xs text-text-secondary leading-relaxed line-clamp-2">
                  {evt.description}
                </p>

                <div className="pt-2 flex items-center justify-between text-xs font-mono text-text-muted border-t border-border/40">
                  <div className="flex items-center gap-3">
                    <span className="flex items-center gap-1">
                      <Globe2 className="w-3 h-3 text-text-muted" />
                      <span>{evt.source_ids.length} Sources</span>
                    </span>
                    <span>•</span>
                    <span>{evt.origin_ids.length} Independent Origins</span>
                    <span>•</span>
                    <span>Discovered {discoveredFormatted}</span>
                  </div>

                  {evt.sessionId && (
                    <Link
                      to={`/research/${evt.sessionId}`}
                      className="text-accent hover:text-accent-hover inline-flex items-center gap-1 font-sans font-medium text-xs transition-colors"
                    >
                      <span>Session Briefing</span>
                      <ArrowRight className="w-3 h-3" />
                    </Link>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

