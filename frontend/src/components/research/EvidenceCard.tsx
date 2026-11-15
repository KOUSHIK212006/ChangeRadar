import React from 'react';
import { SourceRecord, SourceOriginRecord } from '../../types/research';
import { ExternalLink, ShieldCheck, AlertCircle } from 'lucide-react';

interface EvidenceCardProps {
  source: SourceRecord;
  origin?: SourceOriginRecord;
}

export const EvidenceCard: React.FC<EvidenceCardProps> = ({ source, origin }) => {
  const publishedDateText = source.published_at
    ? new Date(source.published_at).toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      })
    : 'Unknown publication date';

  const discoveredDateText = new Date(source.discovered_at).toLocaleString(
    undefined,
    {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }
  );

  return (
    <div className="radar-card p-5 space-y-3.5 hover:border-border-active transition-colors">
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono text-xs font-semibold text-accent uppercase">
              {source.publisher}
            </span>
            {source.is_syndicated ? (
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-status-warning/15 text-status-warning border border-status-warning/30 flex items-center gap-1">
                <AlertCircle className="w-3 h-3" />
                <span>Syndicated / Republication ({Math.round(source.syndication_confidence * 100)}% match)</span>
              </span>
            ) : (
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-status-success/15 text-status-success border border-status-success/30 flex items-center gap-1">
                <ShieldCheck className="w-3 h-3" />
                <span>Primary Document</span>
              </span>
            )}
          </div>
          <h4 className="font-heading font-medium text-base text-text-primary leading-snug">
            {source.title}
          </h4>
        </div>

        <a
          href={source.canonical_url}
          target="_blank"
          rel="noopener noreferrer"
          className="radar-button-secondary text-xs py-1.5 px-2.5 shrink-0"
          title="Open canonical source document in new tab"
        >
          <span>Source</span>
          <ExternalLink className="w-3 h-3 text-accent" />
        </a>
      </div>

      {/* Snippet */}
      <blockquote className="p-3 rounded-lg bg-bg-elevated/70 border border-border text-xs text-text-secondary italic leading-relaxed">
        "{source.snippet}"
      </blockquote>

      {/* Provenance Metadata Breakdown */}
      <div className="pt-2 border-t border-border/40 grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs font-mono text-text-muted">
        <div className="space-y-0.5 truncate">
          <span className="text-[10px] uppercase text-text-muted block">Origin Cluster</span>
          <span className="text-text-primary truncate block font-medium">
            {origin?.label || 'Direct Publisher'}
          </span>
        </div>

        <div className="space-y-0.5">
          <span className="text-[10px] uppercase text-text-muted block">Temporal Provenance</span>
          <span className="text-text-secondary block">
            Pub: {publishedDateText} • Ingested: {discoveredDateText}
          </span>
        </div>
      </div>

      <div className="text-[10px] font-mono text-text-muted truncate pt-1 border-t border-border/20">
        Canonical: <span className="text-text-secondary">{source.canonical_url}</span>
      </div>
    </div>
  );
};

