import React from 'react';
import { CoverageReport } from '../../types/research';
import { AlertTriangle, Info, Search } from 'lucide-react';

interface CoverageAuditCardProps {
  coverage: CoverageReport;
}

export const CoverageAuditCard: React.FC<CoverageAuditCardProps> = ({ coverage }) => {
  const diversityPercent = Math.round(coverage.origin_diversity_score * 100);

  return (
    <div className="radar-card p-6 md:p-8 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border/60 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-heading font-semibold text-lg text-text-primary">
              Coverage & Limitations Audit
            </h3>
            <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-bg-elevated text-text-secondary border border-border">
              Audit Transparency
            </span>
          </div>
          <p className="text-xs text-text-secondary mt-1">
            Explicit audit of search scope, origin diversity, and unanswered questions
          </p>
        </div>

        <div className="flex items-center gap-3 text-xs font-mono">
          <div className="p-2 rounded-lg bg-bg-elevated border border-border flex items-center gap-2">
            <Search className="w-3.5 h-3.5 text-accent" />
            <span>
              {coverage.executed_searches} / {coverage.planned_searches} Searches Executed
            </span>
          </div>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="p-3.5 rounded-lg bg-bg-elevated/50 border border-border space-y-1">
          <span className="text-[10px] font-mono uppercase text-text-muted block">
            Time Window
          </span>
          <span className="font-mono font-semibold text-base text-text-primary">
            {coverage.time_window_days} Days
          </span>
        </div>

        <div className="p-3.5 rounded-lg bg-bg-elevated/50 border border-border space-y-1">
          <span className="text-[10px] font-mono uppercase text-text-muted block">
            Failed Queries
          </span>
          <span
            className={`font-mono font-semibold text-base ${
              coverage.failed_searches > 0 ? 'text-status-warning' : 'text-status-success'
            }`}
          >
            {coverage.failed_searches}
          </span>
        </div>

        <div className="p-3.5 rounded-lg bg-bg-elevated/50 border border-border space-y-1">
          <span className="text-[10px] font-mono uppercase text-text-muted block">
            Origin Diversity
          </span>
          <div className="flex items-center gap-1.5 font-mono font-semibold text-base text-text-primary">
            <span>{diversityPercent}%</span>
            <span className="text-[10px] font-normal text-text-muted">
              ({diversityPercent >= 60 ? 'Healthy' : 'Concentrated'})
            </span>
          </div>
        </div>

        <div className="p-3.5 rounded-lg bg-bg-elevated/50 border border-border space-y-1">
          <span className="text-[10px] font-mono uppercase text-text-muted block">
            Source Types
          </span>
          <div className="text-xs font-mono text-text-secondary capitalize truncate">
            {coverage.source_types_found.join(', ') || 'News, filings'}
          </div>
        </div>
      </div>

      {/* Warnings & Syndication Caveats */}
      {coverage.warnings.length > 0 && (
        <div className="space-y-2">
          <span className="text-xs font-mono uppercase tracking-wider text-status-warning flex items-center gap-1.5 font-semibold">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>Search & Syndication Caveats:</span>
          </span>
          <div className="space-y-2">
            {coverage.warnings.map((w, idx) => (
              <div
                key={idx}
                className="p-3 rounded-lg bg-[#2F2718]/40 border border-[#685227]/70 text-xs text-text-primary font-mono leading-relaxed"
              >
                ⚠️ {w}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Known Information Gaps */}
      <div className="space-y-2 pt-2 border-t border-border/40">
        <span className="text-xs font-mono uppercase tracking-wider text-text-muted flex items-center gap-1.5">
          <Info className="w-3.5 h-3.5 text-accent" />
          <span>Known Intelligence Gaps & Unanswered Angles:</span>
        </span>
        {coverage.gaps.length === 0 ? (
          <p className="text-xs text-text-secondary italic">
            No severe blind spots identified within the configured search window.
          </p>
        ) : (
          <ul className="space-y-2 text-xs text-text-secondary">
            {coverage.gaps.map((gap, idx) => (
              <li
                key={idx}
                className="p-3 rounded-lg bg-bg-elevated/40 border border-border flex items-start gap-2.5 leading-relaxed"
              >
                <span className="text-accent font-bold">•</span>
                <span className="text-text-primary">{gap}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="text-[11px] font-mono text-text-muted italic border-t border-border/40 pt-3">
        ChangeRadar Principle: Absence of search results does not prove absence of event occurrences. Coverage report shows the exact operational boundary examined.
      </div>
    </div>
  );
};

