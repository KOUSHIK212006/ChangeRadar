import React from 'react';
import { DeltaRecord, ExtractedEvent, ExtractedClaim } from '../../types/research';
import {
  CheckCheck,
  AlertTriangle,
  Sparkles,
  RefreshCw,
  Clock,
  ShieldAlert,
} from 'lucide-react';
import { useMarkReviewed } from '../../hooks/useResearch';

interface PersonalDeltaCardProps {
  sessionId: string;
  delta?: DeltaRecord | null;
  lastReviewedAt?: string | null;
  events: ExtractedEvent[];
  claims: ExtractedClaim[];
}

export const PersonalDeltaCard: React.FC<PersonalDeltaCardProps> = ({
  sessionId,
  delta,
  lastReviewedAt,
  events,
  claims,
}) => {
  const markReviewedMutation = useMarkReviewed(sessionId);

  const getEventTitle = (id: string) => {
    return events.find((e) => e.event_id === id)?.title || id;
  };

  const getClaimText = (id: string) => {
    return claims.find((c) => c.claim_id === id)?.text || id;
  };

  const formattedBaselineDate = lastReviewedAt
    ? new Date(lastReviewedAt).toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    : null;

  return (
    <div className="radar-card p-6 md:p-8 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border/60 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <h3 className="font-heading font-semibold text-lg text-text-primary">
              Personal Review Delta
            </h3>
            <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-accent/15 text-accent border border-accent/30 uppercase">
              Delta Intelligence
            </span>
          </div>
          <p className="text-xs text-text-secondary mt-1">
            {formattedBaselineDate ? (
              <>
                Net developments detected since your last review on{' '}
                <span className="font-mono text-text-primary font-medium">
                  {formattedBaselineDate}
                </span>
              </>
            ) : (
              'Initial investigation run. No previous baseline exists. Reviewing now establishes your baseline for future deltas.'
            )}
          </p>
        </div>

        <button
          type="button"
          onClick={() => markReviewedMutation.mutate()}
          disabled={markReviewedMutation.isPending}
          className="radar-button-primary text-xs py-2 px-3.5 shrink-0"
          title="Update baseline timestamp to current briefing state"
        >
          {markReviewedMutation.isPending ? (
            <span>Updating Baseline...</span>
          ) : (
            <>
              <CheckCheck className="w-4 h-4" />
              <span>Mark Briefing as Reviewed</span>
            </>
          )}
        </button>
      </div>

      {/* Delta Categories Breakdown */}
      {!delta ? (
        <div className="p-4 rounded-xl bg-bg-elevated/40 border border-border text-xs text-text-secondary leading-relaxed">
          This is an initial research run for this subject. All {events.length} extracted events and {claims.length} atomic claims form your starting baseline. Click{' '}
          <strong className="text-text-primary">"Mark Briefing as Reviewed"</strong> above once inspected so subsequent runs can isolate new deltas.
        </div>
      ) : delta.no_material_change ? (
        <div className="p-5 rounded-xl bg-[#182B22]/50 border border-[#2D5A43] text-status-success text-xs flex items-center gap-3 font-mono">
          <CheckCheck className="w-5 h-5 shrink-0" />
          <span>
            NO MATERIAL CHANGES DETECTED: Primary sources confirm no new material events or altered claim statuses since your baseline.
          </span>
        </div>
      ) : delta.comparison_incomplete ? (
        <div className="p-5 rounded-xl bg-status-warning/10 border border-status-warning/40 text-status-warning text-xs flex items-center gap-3 font-mono">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          <span>
            PARTIAL DELTA COMPARISON: {delta.incompleteness_reason || 'Previous baseline or current run was incomplete.'}
          </span>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* New Events */}
          <div className="p-4 rounded-xl bg-bg-elevated/40 border border-border space-y-2.5">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-accent font-semibold flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5" />
                <span>NEW EVENTS ({delta.new_events.length})</span>
              </span>
              <span className="text-text-muted">Not in baseline</span>
            </div>
            {delta.new_events.length === 0 ? (
              <p className="text-xs text-text-muted italic">No new events since baseline.</p>
            ) : (
              <ul className="space-y-1.5 text-xs text-text-primary">
                {delta.new_events.map((id) => (
                  <li key={id} className="flex items-start gap-1.5 leading-snug">
                    <span className="text-accent">•</span>
                    <span>{getEventTitle(id)}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Updated Events */}
          <div className="p-4 rounded-xl bg-bg-elevated/40 border border-border space-y-2.5">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-status-info font-semibold flex items-center gap-1.5">
                <RefreshCw className="w-3.5 h-3.5" />
                <span>UPDATED EVENTS ({delta.updated_events.length})</span>
              </span>
              <span className="text-text-muted">Changed status/revisions</span>
            </div>
            {delta.updated_events.length === 0 ? (
              <p className="text-xs text-text-muted italic">No updated events since baseline.</p>
            ) : (
              <ul className="space-y-1.5 text-xs text-text-primary">
                {delta.updated_events.map((id) => (
                  <li key={id} className="flex items-start gap-1.5 leading-snug">
                    <span className="text-status-info">•</span>
                    <span>{getEventTitle(id)}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* New Evidence for Existing Claims */}
          <div className="p-4 rounded-xl bg-bg-elevated/40 border border-border space-y-2.5">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-status-success font-semibold flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5" />
                <span>NEW EVIDENCE DISCOVERED ({delta.new_evidence_for_claims.length})</span>
              </span>
              <span className="text-text-muted">Fresh corroborations</span>
            </div>
            {delta.new_evidence_for_claims.length === 0 ? (
              <p className="text-xs text-text-muted italic">No new evidence excerpts added.</p>
            ) : (
              <ul className="space-y-1.5 text-xs text-text-primary">
                {delta.new_evidence_for_claims.map((id) => (
                  <li key={id} className="flex items-start gap-1.5 leading-snug">
                    <span className="text-status-success">•</span>
                    <span>"{getClaimText(id)}"</span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Changed Assessments */}
          <div className="p-4 rounded-xl bg-bg-elevated/40 border border-border space-y-2.5">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-status-warning font-semibold flex items-center gap-1.5">
                <ShieldAlert className="w-3.5 h-3.5" />
                <span>STATUS SHIFTS ({delta.changed_assessments.length})</span>
              </span>
              <span className="text-text-muted">Verification changes</span>
            </div>
            {delta.changed_assessments.length === 0 ? (
              <p className="text-xs text-text-muted italic">No claim assessment status changes.</p>
            ) : (
              <ul className="space-y-1.5 text-xs text-text-primary">
                {delta.changed_assessments.map((id) => (
                  <li key={id} className="flex items-start gap-1.5 leading-snug">
                    <span className="text-status-warning">•</span>
                    <span>"{getClaimText(id)}"</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

