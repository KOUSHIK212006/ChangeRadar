import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CreateSessionPayload, OwnershipScope } from '../../types/research';
import { useCreateSession } from '../../hooks/useResearch';
import {
  Lock,
  Users,
  Plus,
  Trash2,
  ArrowRight,
  Info,
} from 'lucide-react';

export const ResearchForm: React.FC = () => {
  const navigate = useNavigate();
  const createMutation = useCreateSession();

  const [targetName, setTargetName] = useState('');
  const [targetType, setTargetType] = useState('company');
  const [meetingContext, setMeetingContext] = useState('');
  const [timeWindowDays, setTimeWindowDays] = useState(30);
  const [scope, setScope] = useState<OwnershipScope>('PERSONAL');
  const [questions, setQuestions] = useState<string[]>(['']);
  const [talkingPoints, setTalkingPoints] = useState<string[]>(['']);
  const [validationError, setValidationError] = useState<string | null>(null);

  const handleAddQuestion = () => setQuestions([...questions, '']);
  const handleRemoveQuestion = (idx: number) => {
    setQuestions(questions.filter((_, i) => i !== idx));
  };
  const handleQuestionChange = (idx: number, val: string) => {
    const updated = [...questions];
    updated[idx] = val;
    setQuestions(updated);
  };

  const handleAddTalkingPoint = () => setTalkingPoints([...talkingPoints, '']);
  const handleRemoveTalkingPoint = (idx: number) => {
    setTalkingPoints(talkingPoints.filter((_, i) => i !== idx));
  };
  const handleTalkingPointChange = (idx: number, val: string) => {
    const updated = [...talkingPoints];
    updated[idx] = val;
    setTalkingPoints(updated);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    if (!targetName.trim()) {
      setValidationError('Please enter a target entity, company, or topic name.');
      return;
    }

    const payload: CreateSessionPayload = {
      target_name: targetName.trim(),
      target_type: targetType,
      meeting_context: meetingContext.trim(),
      time_window_days: timeWindowDays,
      research_questions: questions.map((q) => q.trim()).filter(Boolean),
      talking_points: talkingPoints.map((tp) => tp.trim()).filter(Boolean),
      scope,
    };

    try {
      const created = await createMutation.mutateAsync(payload);
      navigate(`/research/${created.id}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to launch research session.';
      setValidationError(msg);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-8 max-w-4xl mx-auto">
      {validationError && (
        <div
          className="p-4 rounded-xl bg-status-danger/10 border border-status-danger/30 text-status-danger text-sm flex items-center gap-3"
          role="alert"
        >
          <Info className="w-5 h-5 shrink-0" />
          <span>{validationError}</span>
        </div>
      )}

      {/* Target Entity Card */}
      <div className="radar-card p-6 md:p-8 space-y-6">
        <div className="border-b border-border/60 pb-4">
          <h2 className="font-heading font-semibold text-lg text-text-primary">
            Research Target & Parameters
          </h2>
          <p className="text-xs text-text-secondary mt-1">
            Specify the company, person, or market topic you are meeting about.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="md:col-span-2 space-y-2">
            <label
              htmlFor="targetName"
              className="block text-xs font-mono uppercase tracking-wider text-text-secondary"
            >
              Target Name <span className="text-accent">*</span>
            </label>
            <input
              id="targetName"
              type="text"
              required
              value={targetName}
              onChange={(e) => setTargetName(e.target.value)}
              placeholder="e.g. Acme Corp, Dr. Elena Rostova, Autonomous Vehicles"
              className="radar-input w-full text-base font-medium"
            />
          </div>

          <div className="space-y-2">
            <label
              htmlFor="targetType"
              className="block text-xs font-mono uppercase tracking-wider text-text-secondary"
            >
              Entity Classification
            </label>
            <select
              id="targetType"
              value={targetType}
              onChange={(e) => setTargetType(e.target.value)}
              className="radar-input w-full"
            >
              <option value="company">Company / Organization</option>
              <option value="person">Executive / Individual</option>
              <option value="topic">Market / Topic</option>
              <option value="regulatory">Regulatory / Compliance</option>
            </select>
          </div>
        </div>

        {/* Meeting Purpose */}
        <div className="space-y-2">
          <label
            htmlFor="meetingContext"
            className="block text-xs font-mono uppercase tracking-wider text-text-secondary"
          >
            Meeting Context & Strategic Objective
          </label>
          <textarea
            id="meetingContext"
            rows={3}
            value={meetingContext}
            onChange={(e) => setMeetingContext(e.target.value)}
            placeholder="e.g. Commercial partnership discussion with VP of Global Strategy; reviewing recent APAC expansion and Q3 margin performance."
            className="radar-input w-full resize-none text-sm"
          />
          <p className="text-xs text-text-muted">
            The intelligence engine uses this context to prioritize material developments over irrelevant noise.
          </p>
        </div>

        {/* Time Window & Scope */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
          <div className="space-y-2">
            <label
              htmlFor="timeWindow"
              className="block text-xs font-mono uppercase tracking-wider text-text-secondary"
            >
              Temporal Search Scope
            </label>
            <select
              id="timeWindow"
              value={timeWindowDays}
              onChange={(e) => setTimeWindowDays(Number(e.target.value))}
              className="radar-input w-full font-mono text-xs"
            >
              <option value={7}>Past 7 days (High recency focus)</option>
              <option value={14}>Past 14 days</option>
              <option value={30}>Past 30 days (Recommended baseline)</option>
              <option value={60}>Past 60 days</option>
              <option value={90}>Past 90 days (Quarterly retrospective)</option>
            </select>
          </div>

          <div className="space-y-2">
            <span className="block text-xs font-mono uppercase tracking-wider text-text-secondary">
              Ownership Boundary
            </span>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setScope('PERSONAL')}
                className={`flex items-center justify-center gap-2 p-2.5 rounded-lg border text-xs font-medium transition-colors ${
                  scope === 'PERSONAL'
                    ? 'bg-accent/10 border-accent text-accent'
                    : 'bg-bg-elevated border-border text-text-secondary hover:text-text-primary'
                }`}
              >
                <Lock className="w-3.5 h-3.5" />
                <span>Personal</span>
              </button>
              <button
                type="button"
                onClick={() => setScope('WORKSPACE')}
                className={`flex items-center justify-center gap-2 p-2.5 rounded-lg border text-xs font-medium transition-colors ${
                  scope === 'WORKSPACE'
                    ? 'bg-status-info/10 border-status-info text-status-info'
                    : 'bg-bg-elevated border-border text-text-secondary hover:text-text-primary'
                }`}
              >
                <Users className="w-3.5 h-3.5" />
                <span>Workspace</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Baseline Intelligence Principle Callout */}
      <div className="radar-card p-5 border-border/80 bg-bg-elevated/40 flex items-start gap-4">
        <Info className="w-5 h-5 text-accent shrink-0 mt-0.5" />
        <div className="space-y-1 text-xs text-text-secondary leading-relaxed">
          <strong className="text-text-primary font-medium">
            Review Baseline Principle:
          </strong>{' '}
          ChangeRadar measures deltas relative to your{' '}
          <em className="text-text-primary">last actively reviewed state</em>, not merely the previous automated run. If this is your first investigation of {targetName || 'this subject'}, this run will establish your initial review baseline.
        </div>
      </div>

      {/* Specific Questions Card */}
      <div className="radar-card p-6 md:p-8 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-heading font-semibold text-base text-text-primary">
              Specific Research Questions (Optional)
            </h3>
            <p className="text-xs text-text-secondary">
              Direct the intelligence engine toward particular areas of investigation.
            </p>
          </div>
          <button
            type="button"
            onClick={handleAddQuestion}
            className="text-xs text-accent hover:text-accent-hover font-mono flex items-center gap-1 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Question</span>
          </button>
        </div>

        <div className="space-y-3">
          {questions.map((q, idx) => (
            <div key={idx} className="flex items-center gap-2">
              <input
                type="text"
                value={q}
                onChange={(e) => handleQuestionChange(idx, e.target.value)}
                placeholder={`e.g. Any updates on executive departures or leadership turnover?`}
                className="radar-input flex-1 text-xs"
              />
              {questions.length > 1 && (
                <button
                  type="button"
                  onClick={() => handleRemoveQuestion(idx)}
                  className="p-2 text-text-muted hover:text-status-danger transition-colors"
                  aria-label="Remove question"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Talking Points to Stress Test */}
      <div className="radar-card p-6 md:p-8 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-heading font-semibold text-base text-text-primary">
              Pre-Meeting Talking Points (Optional)
            </h3>
            <p className="text-xs text-text-secondary">
              Enter statements you plan to make. We will stress-test each against verified evidence and suggest grounded alternatives if contradicted.
            </p>
          </div>
          <button
            type="button"
            onClick={handleAddTalkingPoint}
            className="text-xs text-accent hover:text-accent-hover font-mono flex items-center gap-1 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Talking Point</span>
          </button>
        </div>

        <div className="space-y-3">
          {talkingPoints.map((tp, idx) => (
            <div key={idx} className="flex items-center gap-2">
              <input
                type="text"
                value={tp}
                onChange={(e) => handleTalkingPointChange(idx, e.target.value)}
                placeholder={`e.g. Acme Corp achieved 20% revenue growth in Q3`}
                className="radar-input flex-1 text-xs"
              />
              {talkingPoints.length > 1 && (
                <button
                  type="button"
                  onClick={() => handleRemoveTalkingPoint(idx)}
                  className="p-2 text-text-muted hover:text-status-danger transition-colors"
                  aria-label="Remove talking point"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex items-center justify-end gap-4 pt-4 border-t border-border">
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="radar-button-secondary text-sm"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={createMutation.isPending}
          className="radar-button-primary text-sm min-w-[180px]"
        >
          {createMutation.isPending ? (
            <span>Dispatching Job...</span>
          ) : (
            <>
              <span>Launch Research Run</span>
              <ArrowRight className="w-4 h-4" />
            </>
          )}
        </button>
      </div>
    </form>
  );
};

