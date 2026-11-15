import React, { useState } from 'react';
import { StressTestResult } from '../../types/research';
import { useStressTest } from '../../hooks/useResearch';
import { Badge } from '../common/Badge';
import {
  Scale,
  Sparkles,
  Copy,
  Check,
  AlertTriangle,
  HelpCircle,
  Loader2,
} from 'lucide-react';

interface TalkingPointTesterProps {
  sessionId: string;
  initialResults?: StressTestResult | null;
}

export const TalkingPointTester: React.FC<TalkingPointTesterProps> = ({
  sessionId,
  initialResults,
}) => {
  const stressTestMutation = useStressTest(sessionId);
  const [talkingPointsText, setTalkingPointsText] = useState('');
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const [activeResults, setActiveResults] = useState<StressTestResult | null>(
    initialResults || null
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const rawLines = talkingPointsText
      .split('\n')
      .map((l) => l.trim())
      .filter(Boolean);

    if (rawLines.length === 0) return;

    try {
      const res = await stressTestMutation.mutateAsync({
        talking_points: rawLines,
      });
      setActiveResults(res);
    } catch {
      // Mutation retains text in textarea so user doesn't lose draft
    }
  };

  const handleCopy = (text: string, index: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  return (
    <div className="radar-card p-6 md:p-8 space-y-6">
      <div className="border-b border-border/60 pb-5">
        <div className="flex items-center gap-2">
          <h3 className="font-heading font-semibold text-lg text-text-primary">
            Talking-Point Stress Test
          </h3>
          <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-accent/15 text-accent border border-accent/30 uppercase">
            Defensibility Engine
          </span>
        </div>
        <p className="text-xs text-text-secondary mt-1">
          Submit prospective statements to identify contradictions, factual vulnerabilities, and grounded alternatives before your meeting.
        </p>
      </div>

      {/* Input Box */}
      <form onSubmit={handleSubmit} className="space-y-3">
        <label
          htmlFor="stressPointsInput"
          className="block text-xs font-mono uppercase tracking-wider text-text-muted"
        >
          Enter Planned Talking Points (one statement per line)
        </label>
        <textarea
          id="stressPointsInput"
          rows={3}
          value={talkingPointsText}
          onChange={(e) => setTalkingPointsText(e.target.value)}
          placeholder={`e.g.\nAcme Corp achieved 20% revenue growth in Q3.\nThey have already finalized a permanent CFO successor.`}
          className="radar-input w-full text-xs font-mono resize-y"
        />

        <div className="flex items-center justify-between">
          <span className="text-[11px] font-mono text-text-muted">
            {talkingPointsText.split('\n').filter((l) => l.trim()).length} point(s) staged
          </span>
          <button
            type="submit"
            disabled={stressTestMutation.isPending || !talkingPointsText.trim()}
            className="radar-button-primary text-xs py-2 px-3.5"
          >
            {stressTestMutation.isPending ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Stress-Testing Points...</span>
              </>
            ) : (
              <>
                <Scale className="w-3.5 h-3.5" />
                <span>Run Stress Test</span>
              </>
            )}
          </button>
        </div>
      </form>

      {/* Results Display */}
      {activeResults && activeResults.points.length > 0 && (
        <div className="space-y-4 pt-4 border-t border-border/60">
          <h4 className="text-xs font-mono uppercase tracking-wider text-text-muted">
            Evidence-Grounded Assessments ({activeResults.points.length})
          </h4>

          <div className="space-y-4">
            {activeResults.points.map((pt, idx) => {
              const primaryAssessment = pt.assessments[0];
              const isContradicted =
                primaryAssessment?.assessment === 'CONTRADICTED';
              const isSupported =
                primaryAssessment?.assessment === 'SUPPORTED';
              const isInsufficient =
                pt.needs_more_research ||
                primaryAssessment?.assessment === 'INSUFFICIENT';

              return (
                <div
                  key={idx}
                  className={`p-5 rounded-xl border transition-colors space-y-4 ${
                    isContradicted
                      ? 'bg-[#341814]/30 border-[#782D1E]/80'
                      : isSupported
                      ? 'bg-[#182B22]/30 border-[#2D5A43]/80'
                      : 'bg-bg-elevated/40 border-border'
                  }`}
                >
                  {/* Original Point */}
                  <div className="space-y-1">
                    <div className="flex items-center justify-between gap-2 flex-wrap">
                      <span className="text-[10px] font-mono uppercase text-text-muted">
                        Original Statement #{idx + 1}
                      </span>
                      {primaryAssessment && (
                        <Badge
                          type="evidence"
                          value={primaryAssessment.assessment}
                          size="sm"
                        />
                      )}
                    </div>
                    <p className="font-heading font-semibold text-sm md:text-base text-text-primary">
                      "{pt.original_point}"
                    </p>
                  </div>

                  {/* Rationale and Evidence */}
                  {primaryAssessment && (
                    <div className="p-3.5 rounded-lg bg-bg-secondary border border-border/80 text-xs space-y-2">
                      <div className="flex items-center gap-1.5 text-text-muted font-mono text-[11px]">
                        <HelpCircle className="w-3.5 h-3.5 text-accent" />
                        <span>EVIDENCE VERIFICATION RATIONALE:</span>
                      </div>
                      <p className="text-text-primary leading-relaxed font-sans">
                        {primaryAssessment.assessment_rationale}
                      </p>

                      {primaryAssessment.evidence.map((ev) => (
                        <blockquote
                          key={ev.evidence_id}
                          className="pt-1.5 border-t border-border/40 text-text-secondary italic text-[11px]"
                        >
                          "{ev.excerpt}"
                        </blockquote>
                      ))}
                    </div>
                  )}

                  {/* Grounded Revision Suggestion */}
                  {pt.suggested_wording && (
                    <div className="p-3.5 rounded-lg bg-bg-elevated border border-accent/40 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-mono uppercase text-accent font-semibold flex items-center gap-1.5">
                          <Sparkles className="w-3.5 h-3.5" />
                          <span>GROUNDED DEFENSIVE REWRITE:</span>
                        </span>
                        <button
                          type="button"
                          onClick={() => handleCopy(pt.suggested_wording!, idx)}
                          className="text-xs font-mono text-text-secondary hover:text-text-primary flex items-center gap-1 transition-colors"
                        >
                          {copiedIndex === idx ? (
                            <>
                              <Check className="w-3.5 h-3.5 text-status-success" />
                              <span className="text-status-success">Copied</span>
                            </>
                          ) : (
                            <>
                              <Copy className="w-3.5 h-3.5" />
                              <span>Copy Wording</span>
                            </>
                          )}
                        </button>
                      </div>
                      <p className="text-xs text-text-primary leading-relaxed">
                        {pt.suggested_wording}
                      </p>
                    </div>
                  )}

                  {isInsufficient && (
                    <div className="flex items-center gap-2 text-xs font-mono text-status-warning bg-status-warning/10 p-2.5 rounded border border-status-warning/30">
                      <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                      <span>
                        INSUFFICIENT EVIDENCE: Claims could not be matched with high certainty to current search index. Qualification recommended.
                      </span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

