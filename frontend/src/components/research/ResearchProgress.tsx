import React from 'react';
import { ResearchJob } from '../../types/research';
import { Badge } from '../common/Badge';
import {
  CheckCircle2,
  Clock,
  Loader2,
  AlertOctagon,
  Search,
  FileText,
  ShieldCheck,
  Scale,
  Sparkles,
} from 'lucide-react';

interface ResearchProgressProps {
  job: ResearchJob;
  onRefresh?: () => void;
}

interface StageStep {
  key: string;
  label: string;
  desc: string;
  icon: React.ElementType;
}

const STAGES: StageStep[] = [
  {
    key: 'REQUEST_ACCEPTED',
    label: 'Request Accepted',
    desc: 'Target validation and ownership boundary confirmed',
    icon: Clock,
  },
  {
    key: 'SEARCH_PLANNING',
    label: 'Search Planning',
    desc: 'Constructing multi-angle queries across primary indexes',
    icon: Search,
  },
  {
    key: 'SOURCE_COLLECTION',
    label: 'Source Collection & Syndication Check',
    desc: 'Clustering duplicate press releases & syndicated copies',
    icon: FileText,
  },
  {
    key: 'CLAIM_EXTRACTION',
    label: 'Atomic Claim Extraction',
    desc: 'Isolating factual propositions from narrative statements',
    icon: Sparkles,
  },
  {
    key: 'EVIDENCE_ASSESSMENT',
    label: 'Evidence Grounding & Stance Linking',
    desc: 'Evaluating claims as Supported, Contradicted, or Insufficient',
    icon: Scale,
  },
  {
    key: 'TEMPORAL_COMPARISON',
    label: 'Temporal Baseline Delta',
    desc: 'Computing net changes against last reviewed snapshot',
    icon: Clock,
  },
  {
    key: 'COVERAGE_AUDIT',
    label: 'Coverage & Gaps Audit',
    desc: 'Assessing source diversity and reporting search limitations',
    icon: ShieldCheck,
  },
  {
    key: 'BRIEFING_GENERATION',
    label: 'Briefing Synthesis',
    desc: 'Compiling structured executive briefing and talking points',
    icon: CheckCircle2,
  },
];

export const ResearchProgress: React.FC<ResearchProgressProps> = ({ job }) => {
  const getStageIndex = (stage: string) => {
    if (stage === 'COMPLETE') return STAGES.length;
    const idx = STAGES.findIndex((s) => s.key === stage);
    return idx >= 0 ? idx : 0;
  };

  const currentIdx = getStageIndex(job.current_stage);

  return (
    <div className="radar-card p-6 md:p-8 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border/60 pb-5">
        <div className="space-y-1">
          <div className="flex items-center gap-2.5">
            <h2 className="font-heading font-semibold text-xl text-text-primary">
              Intelligence Pipeline Status
            </h2>
            <Badge type="job" value={job.status} />
          </div>
          <p className="text-xs font-mono text-text-secondary">
            Job ID: {job.id} • Attempt {job.attempt_count}
          </p>
        </div>

        {job.status === 'RUNNING' && (
          <div className="flex items-center gap-2 text-xs font-mono text-accent bg-accent/10 px-3 py-1.5 rounded-lg border border-accent/30 shrink-0">
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            <span>POLLING LIVE PROGRESS (3s)</span>
          </div>
        )}
      </div>

      {/* Progress Bar */}
      <div className="space-y-2">
        <div className="flex justify-between text-xs font-mono text-text-secondary">
          <span>Overall Progress</span>
          <span className="text-text-primary font-medium">{job.progress_pct}%</span>
        </div>
        <div className="h-2 w-full bg-bg-elevated rounded-full overflow-hidden border border-border">
          <div
            className="h-full bg-accent transition-all duration-500 rounded-full"
            style={{ width: `${job.progress_pct}%` }}
          />
        </div>
      </div>

      {/* Error state if failed */}
      {job.error_message && (
        <div className="p-4 rounded-xl bg-status-danger/10 border border-status-danger/30 text-status-danger text-xs font-mono flex items-start gap-3">
          <AlertOctagon className="w-4 h-4 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <span className="font-semibold block">Pipeline Notice:</span>
            <span>{job.error_message}</span>
          </div>
        </div>
      )}

      {/* Stage Flow */}
      <div className="space-y-3 pt-2">
        <h3 className="text-xs font-mono uppercase tracking-wider text-text-muted">
          Execution Lifecycle Stages
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {STAGES.map((stg, idx) => {
            const isCompleted = idx < currentIdx || job.status === 'COMPLETED';
            const isCurrent = idx === currentIdx && job.status === 'RUNNING';

            const Icon = stg.icon;

            return (
              <div
                key={stg.key}
                className={`p-3.5 rounded-lg border flex items-start gap-3 transition-colors ${
                  isCurrent
                    ? 'bg-accent/5 border-accent/50 text-text-primary ring-1 ring-accent/30'
                    : isCompleted
                    ? 'bg-bg-elevated/40 border-border/80 text-text-secondary'
                    : 'bg-bg-primary/40 border-border/40 text-text-muted opacity-60'
                }`}
              >
                <div
                  className={`w-7 h-7 rounded-md flex items-center justify-center shrink-0 text-xs mt-0.5 ${
                    isCurrent
                      ? 'bg-accent text-white'
                      : isCompleted
                      ? 'bg-status-success/20 text-status-success border border-status-success/30'
                      : 'bg-bg-elevated text-text-muted border border-border'
                  }`}
                >
                  {isCurrent ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : isCompleted ? (
                    <CheckCircle2 className="w-3.5 h-3.5" />
                  ) : (
                    <Icon className="w-3.5 h-3.5" />
                  )}
                </div>

                <div className="space-y-0.5 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-xs text-text-primary">
                      {stg.label}
                    </span>
                    {isCurrent && (
                      <span className="text-[10px] font-mono text-accent uppercase font-bold">
                        Current
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-text-secondary leading-snug">
                    {stg.desc}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

