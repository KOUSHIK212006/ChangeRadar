import React, { useState } from 'react';
import {
  ExtractedClaim,
  SourceRecord,
} from '../../types/research';
import { Badge } from '../common/Badge';
import {
  Search,
  Filter,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  HelpCircle,
  Clock,
} from 'lucide-react';

interface ClaimTableProps {
  claims: ExtractedClaim[];
  sources: SourceRecord[];
}

export const ClaimTable: React.FC<ClaimTableProps> = ({ claims, sources }) => {
  const [filterStatus, setFilterStatus] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [expandedClaimId, setExpandedClaimId] = useState<string | null>(
    claims[0]?.claim_id || null
  );

  const getSourceById = (sourceId: string) => {
    return sources.find((s) => s.source_id === sourceId);
  };

  const filteredClaims = claims.filter((claim) => {
    const matchesStatus =
      filterStatus === 'ALL' || claim.assessment === filterStatus;
    const matchesSearch =
      !searchQuery ||
      claim.text.toLowerCase().includes(searchQuery.toLowerCase()) ||
      claim.assessment_rationale.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesStatus && matchesSearch;
  });

  const toggleExpand = (claimId: string) => {
    setExpandedClaimId(expandedClaimId === claimId ? null : claimId);
  };

  return (
    <div className="space-y-4">
      {/* Search and Filter Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 radar-card p-4">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search atomic claims or rationale..."
            className="radar-input w-full pl-9 text-xs"
          />
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <Filter className="w-3.5 h-3.5 text-text-muted" />
          <span className="text-xs font-mono text-text-muted">STATUS:</span>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="radar-input text-xs font-mono py-1.5"
          >
            <option value="ALL">All Statuses ({claims.length})</option>
            <option value="SUPPORTED">Supported</option>
            <option value="PARTIALLY_SUPPORTED">Partially Supported</option>
            <option value="CONTRADICTED">Contradicted</option>
            <option value="INSUFFICIENT">Insufficient Evidence</option>
            <option value="OUTDATED">Outdated / Stale</option>
            <option value="UNVERIFIABLE">Unverifiable</option>
          </select>
        </div>
      </div>

      {/* Claims List */}
      {filteredClaims.length === 0 ? (
        <div className="radar-card p-8 text-center text-text-secondary text-sm">
          No claims matched your search or status filter.
        </div>
      ) : (
        <div className="space-y-3">
          {filteredClaims.map((claim) => {
            const isExpanded = expandedClaimId === claim.claim_id;
            const supportingEvidence = claim.evidence.filter(
              (e) => e.relevance === 'SUPPORTING'
            );
            const contradictingEvidence = claim.evidence.filter(
              (e) => e.relevance === 'CONTRADICTING'
            );

            return (
              <div
                key={claim.claim_id}
                className="radar-card transition-all duration-200 overflow-hidden"
              >
                {/* Header / Summary Bar */}
                <div
                  onClick={() => toggleExpand(claim.claim_id)}
                  className="p-4 md:p-5 flex items-start justify-between gap-4 cursor-pointer hover:bg-bg-elevated/40 transition-colors"
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      toggleExpand(claim.claim_id);
                    }
                  }}
                  aria-expanded={isExpanded}
                >
                  <div className="space-y-2 flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge type="evidence" value={claim.assessment} />
                      <Badge type="volatility" value={claim.volatility} size="sm" />
                      {claim.is_stale && (
                        <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-status-warning/15 text-status-warning border border-status-warning/30 flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          <span>Potentially Stale</span>
                        </span>
                      )}
                      <span className="text-xs font-mono text-text-muted">
                        Claim ID: {claim.claim_id}
                      </span>
                    </div>

                    <p className="font-heading font-medium text-sm md:text-base text-text-primary leading-snug">
                      "{claim.text}"
                    </p>

                    <div className="text-xs text-text-secondary flex items-center gap-4 font-mono">
                      <span>
                        <strong className="text-text-primary">
                          {claim.independent_origin_count}
                        </strong>{' '}
                        Independent Origin{claim.independent_origin_count !== 1 ? 's' : ''}
                      </span>
                      <span>•</span>
                      <span>
                        <strong className="text-text-primary">
                          {claim.source_doc_count}
                        </strong>{' '}
                        Referencing Doc{claim.source_doc_count !== 1 ? 's' : ''}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0 pt-1 text-text-muted">
                    {isExpanded ? (
                      <ChevronUp className="w-5 h-5 text-accent" />
                    ) : (
                      <ChevronDown className="w-5 h-5" />
                    )}
                  </div>
                </div>

                {/* Expanded Details Body */}
                {isExpanded && (
                  <div className="border-t border-border/60 bg-bg-elevated/30 p-5 md:p-6 space-y-5">
                    {/* Engine Assessment Rationale */}
                    <div className="space-y-1.5 p-4 rounded-lg bg-bg-secondary border border-border">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-mono uppercase tracking-wider text-text-muted flex items-center gap-1.5">
                          <HelpCircle className="w-3.5 h-3.5 text-accent" />
                          <span>Assessment Rationale</span>
                        </span>
                        <span className="text-[11px] font-mono text-text-muted" title="Internal LLM parsing confidence (not evidence proof)">
                          Diagnostic Parsing Confidence: {Math.round(claim.llm_confidence * 100)}%
                        </span>
                      </div>
                      <p className="text-sm text-text-primary leading-relaxed font-sans">
                        {claim.assessment_rationale}
                      </p>
                    </div>

                    {/* Contradicting Evidence (Highlighted First if present) */}
                    {contradictingEvidence.length > 0 && (
                      <div className="space-y-2">
                        <div className="flex items-center gap-2 text-xs font-mono text-status-danger font-semibold">
                          <XCircle className="w-4 h-4" />
                          <span>CONTRADICTING PRIMARY EVIDENCE ({contradictingEvidence.length})</span>
                        </div>
                        <div className="space-y-2 pl-3 border-l-2 border-status-danger/60">
                          {contradictingEvidence.map((ev) => {
                            const src = getSourceById(ev.source_id);
                            return (
                              <div
                                key={ev.evidence_id}
                                className="p-3 rounded-lg bg-[#341814]/50 border border-[#782D1E]/60 space-y-2"
                              >
                                <blockquote className="text-xs text-text-primary italic leading-relaxed">
                                  "{ev.excerpt}"
                                </blockquote>
                                {src && (
                                  <div className="flex items-center justify-between text-[11px] font-mono text-text-muted pt-1 border-t border-[#782D1E]/40">
                                    <span className="text-text-secondary truncate">
                                      Source: {src.publisher} — {src.title}
                                    </span>
                                    <a
                                      href={src.canonical_url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="text-accent hover:underline inline-flex items-center gap-1 shrink-0"
                                    >
                                      <span>Verify Original</span>
                                      <ExternalLink className="w-2.5 h-2.5" />
                                    </a>
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {/* Supporting Evidence */}
                    {supportingEvidence.length > 0 && (
                      <div className="space-y-2">
                        <div className="flex items-center gap-2 text-xs font-mono text-status-success font-semibold">
                          <CheckCircle2 className="w-4 h-4" />
                          <span>SUPPORTING EVIDENCE ({supportingEvidence.length})</span>
                        </div>
                        <div className="space-y-2 pl-3 border-l-2 border-status-success/60">
                          {supportingEvidence.map((ev) => {
                            const src = getSourceById(ev.source_id);
                            return (
                              <div
                                key={ev.evidence_id}
                                className="p-3 rounded-lg bg-[#182B22]/50 border border-[#2D5A43]/60 space-y-2"
                              >
                                <blockquote className="text-xs text-text-primary italic leading-relaxed">
                                  "{ev.excerpt}"
                                </blockquote>
                                {src && (
                                  <div className="flex items-center justify-between text-[11px] font-mono text-text-muted pt-1 border-t border-[#2D5A43]/40">
                                    <span className="text-text-secondary truncate">
                                      Source: {src.publisher} — {src.title}
                                    </span>
                                    <a
                                      href={src.canonical_url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="text-status-success hover:underline inline-flex items-center gap-1 shrink-0"
                                    >
                                      <span>Verify Original</span>
                                      <ExternalLink className="w-2.5 h-2.5" />
                                    </a>
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {/* If no direct evidence excerpts */}
                    {claim.evidence.length === 0 && (
                      <div className="p-3 rounded-lg bg-bg-secondary border border-border text-xs text-text-secondary flex items-center gap-2">
                        <AlertTriangle className="w-4 h-4 text-status-warning shrink-0" />
                        <span>
                          No direct verbatim excerpts were retrieved for this claim. Assessment is based on negative search findings or absence of confirmation.
                        </span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

