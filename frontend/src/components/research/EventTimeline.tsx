import React from 'react';
import {
  ExtractedEvent,
  EventVersionRecord,
  SourceRecord,
  SourceOriginRecord,
} from '../../types/research';
import { Badge } from '../common/Badge';
import {
  Calendar,
  ExternalLink,
  GitBranch,
  Layers,
  AlertTriangle,
  FileText,
} from 'lucide-react';

interface EventTimelineProps {
  events: ExtractedEvent[];
  eventVersions?: EventVersionRecord[];
  sources: SourceRecord[];
  origins: SourceOriginRecord[];
}

export const EventTimeline: React.FC<EventTimelineProps> = ({
  events,
  eventVersions = [],
  sources,
  origins,
}) => {
  const getSourcesForEvent = (sourceIds: string[]) => {
    return sources.filter((s) => sourceIds.includes(s.source_id));
  };

  const getOriginsForEvent = (originIds: string[]) => {
    return origins.filter((o) => originIds.includes(o.origin_id));
  };

  const getVersionsForEvent = (eventId: string) => {
    return eventVersions.filter((v) => v.event_id === eventId);
  };

  if (!events || events.length === 0) {
    return (
      <div className="radar-card p-8 text-center text-text-secondary text-sm">
        No events extracted for this time window.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="border-b border-border/60 pb-3 flex items-center justify-between">
        <div>
          <h3 className="font-heading font-semibold text-lg text-text-primary">
            Event Provenance & Timeline
          </h3>
          <p className="text-xs text-text-secondary">
            Temporal chronology separating event occurrence, publication, and discovery
          </p>
        </div>
        <span className="text-xs font-mono text-text-muted bg-bg-elevated px-2.5 py-1 rounded border border-border">
          {events.length} EVENTS
        </span>
      </div>

      <div className="relative pl-6 space-y-8 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-border">
        {events.map((evt) => {
          const evtSources = getSourcesForEvent(evt.source_ids);
          const evtOrigins = getOriginsForEvent(evt.origin_ids);
          const versions = getVersionsForEvent(evt.event_id);

          const eventDateText = evt.event_at
            ? new Date(evt.event_at).toLocaleDateString(undefined, {
                month: 'short',
                day: 'numeric',
                year: 'numeric',
              })
            : 'Exact date unknown (reported in window)';

          const publishedDateText = evt.published_at
            ? new Date(evt.published_at).toLocaleDateString(undefined, {
                month: 'short',
                day: 'numeric',
                year: 'numeric',
              })
            : 'Publication timestamp missing in source';

          const discoveryText = new Date(evt.discovered_at).toLocaleString(
            undefined,
            {
              month: 'short',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
            }
          );

          return (
            <div key={evt.event_id} className="relative group">
              {/* Timeline marker */}
              <div className="absolute -left-[27px] top-1.5 w-3.5 h-3.5 rounded-full bg-accent border-2 border-bg-primary shadow-sm" />

              <div className="radar-card p-5 md:p-6 space-y-4">
                {/* Header row */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <Badge type="lifecycle" value={evt.lifecycle_status} />
                    {evt.is_disputed && (
                      <span className="inline-flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded bg-status-danger/15 text-status-danger border border-status-danger/30">
                        <AlertTriangle className="w-3 h-3" />
                        <span>Disputed</span>
                      </span>
                    )}
                    {evt.is_uncertain && (
                      <span className="inline-flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded bg-status-warning/15 text-status-warning border border-status-warning/30">
                        <span>Uncertain Timing</span>
                      </span>
                    )}
                  </div>

                  {/* Temporal breakdown */}
                  <div className="flex items-center gap-3 text-xs font-mono text-text-muted flex-wrap">
                    <span
                      className="flex items-center gap-1 text-text-secondary"
                      title="When the real-world event occurred"
                    >
                      <Calendar className="w-3.5 h-3.5 text-accent" />
                      <span>Occurred: {eventDateText}</span>
                    </span>
                    <span>•</span>
                    <span
                      title="Earliest publication in reporting media"
                      className="text-text-muted"
                    >
                      Published: {publishedDateText}
                    </span>
                  </div>
                </div>

                {/* Event Title & Summary */}
                <div className="space-y-1.5">
                  <h4 className="font-heading font-semibold text-base text-text-primary">
                    {evt.title}
                  </h4>
                  <p className="text-sm text-text-secondary leading-relaxed">
                    {evt.description}
                  </p>
                </div>

                {/* Origin vs Document Independence Callout */}
                <div className="p-3 rounded-lg bg-bg-elevated/70 border border-border text-xs space-y-2">
                  <div className="flex items-center justify-between font-mono text-[11px] text-text-muted">
                    <span className="flex items-center gap-1 text-text-secondary">
                      <Layers className="w-3.5 h-3.5 text-accent" />
                      <span>PROVENANCE & INDEPENDENCE AUDIT</span>
                    </span>
                    <span>
                      {evtSources.length} Source Document{evtSources.length !== 1 ? 's' : ''} •{' '}
                      {evtOrigins.length} Independent Origin{evtOrigins.length !== 1 ? 's' : ''}
                    </span>
                  </div>

                  <div className="space-y-1.5 pt-1">
                    {evtOrigins.map((org) => (
                      <div
                        key={org.origin_id}
                        className="flex items-center justify-between text-xs py-1 px-2 rounded bg-bg-secondary border border-border/60"
                      >
                        <span className="text-text-primary truncate font-medium">
                          {org.label}
                        </span>
                        <div className="flex items-center gap-2 shrink-0 text-[11px] font-mono">
                          <span
                            className={
                              org.is_independent
                                ? 'text-status-success'
                                : 'text-status-warning'
                            }
                          >
                            {org.is_independent
                              ? 'Independent Reporting'
                              : 'Shared Origin (Press Release)'}
                          </span>
                          <span className="text-text-muted">
                            ({Math.round(org.independence_confidence * 100)}% conf)
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Sources List */}
                  <div className="pt-2 border-t border-border/40">
                    <span className="text-[11px] font-mono text-text-muted block mb-1.5">
                      Referenced Documents:
                    </span>
                    <div className="flex flex-wrap gap-2">
                      {evtSources.map((src) => (
                        <a
                          key={src.source_id}
                          href={src.canonical_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-bg-elevated hover:bg-bg-elevated/80 border border-border hover:border-accent text-xs text-text-secondary hover:text-text-primary transition-colors font-mono"
                          title={src.snippet}
                        >
                          <FileText className="w-3 h-3 text-accent" />
                          <span className="truncate max-w-[200px]">{src.publisher}: {src.title}</span>
                          <ExternalLink className="w-2.5 h-2.5 text-text-muted shrink-0" />
                        </a>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Event Versions History (if event evolved over time) */}
                {versions.length > 0 && (
                  <div className="pt-3 border-t border-border/40 space-y-2">
                    <span className="text-xs font-mono text-text-muted flex items-center gap-1.5">
                      <GitBranch className="w-3.5 h-3.5 text-accent" />
                      <span>DEVELOPMENT REVISIONS ({versions.length}):</span>
                    </span>
                    <div className="space-y-1.5 pl-2 border-l border-border/60">
                      {versions.map((ver) => (
                        <div
                          key={ver.version_id}
                          className="text-xs text-text-secondary flex items-start gap-2"
                        >
                          <span className="font-mono text-[10px] text-text-muted shrink-0 mt-0.5">
                            {new Date(ver.recorded_at).toLocaleDateString()}
                          </span>
                          <span>{ver.description}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Discovery footer */}
                <div className="pt-2 text-[10px] font-mono text-text-muted flex items-center justify-between border-t border-border/40">
                  <span>ChangeRadar Ingestion Time: {discoveryText}</span>
                  <span className="text-text-muted">Event ID: {evt.event_id}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

