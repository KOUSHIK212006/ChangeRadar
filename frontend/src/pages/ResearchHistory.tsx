import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useSessions } from '../hooks/useResearch';
import { PageHeader } from '../components/common/PageHeader';
import { Badge } from '../components/common/Badge';
import { Loader } from '../components/common/Loader';
import { ErrorState } from '../components/common/ErrorState';
import { researchService } from '../services/researchService';
import {
  Search,
  Filter,
  Plus,
  Clock,
  ArrowUpRight,
  Trash2,
} from 'lucide-react';

export const ResearchHistory: React.FC = () => {
  const navigate = useNavigate();
  const { data: sessions, isLoading, error, refetch } = useSessions();
  const [searchQuery, setSearchQuery] = useState('');
  const [scopeFilter, setScopeFilter] = useState<'ALL' | 'PERSONAL' | 'WORKSPACE'>('ALL');

  if (isLoading) {
    return <Loader label="Loading research history..." size="lg" />;
  }

  if (error || !sessions) {
    return (
      <ErrorState
        title="Failed to Load History"
        message={(error as Error)?.message}
        onRetry={() => refetch()}
      />
    );
  }

  const filteredSessions = sessions.filter((s) => {
    const matchesScope = scopeFilter === 'ALL' || s.scope === scopeFilter;
    const matchesSearch =
      !searchQuery ||
      s.target_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (s.meeting_context && s.meeting_context.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesScope && matchesSearch;
  });

  const handleDelete = async (id: string, name: string) => {
    if (window.confirm(`Are you sure you want to remove the research session for '${name}'?`)) {
      await researchService.deleteSession(id);
      refetch();
    }
  };

  return (
    <div className="space-y-6 animate-fadeIn">
      <PageHeader
        title="Research History & Archive"
        subtitle="Catalog of all intelligence dossiers, review baselines, and entity tracking records."
        breadcrumbs={[
          { label: 'Overview', href: '/' },
          { label: 'Research History' },
        ]}
        actions={
          <button
            type="button"
            onClick={() => navigate('/new')}
            className="radar-button-primary text-xs py-2 px-3.5"
          >
            <Plus className="w-4 h-4" />
            <span>New Research</span>
          </button>
        }
      />

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 radar-card p-4">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by target name, keyword, or meeting context..."
            className="radar-input w-full pl-9 text-xs"
          />
        </div>

        <div className="flex items-center gap-2">
          <Filter className="w-3.5 h-3.5 text-text-muted" />
          <span className="text-xs font-mono text-text-muted">SCOPE:</span>
          <select
            value={scopeFilter}
            onChange={(e) => setScopeFilter(e.target.value as any)}
            className="radar-input text-xs font-mono py-1.5"
          >
            <option value="ALL">All Scopes ({sessions.length})</option>
            <option value="PERSONAL">Personal Only</option>
            <option value="WORKSPACE">Workspace Only</option>
          </select>
        </div>
      </div>

      {/* Sessions Grid / Table */}
      {filteredSessions.length === 0 ? (
        <div className="radar-card p-12 text-center space-y-4">
          <p className="text-sm text-text-secondary">
            No research sessions found matching your filters.
          </p>
          <button
            type="button"
            onClick={() => navigate('/new')}
            className="radar-button-primary text-xs mx-auto"
          >
            Launch Investigation
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredSessions.map((session) => {
            const jobStatus = session.latest_job?.status || 'COMPLETED';
            const updatedDate = new Date(session.updated_at).toLocaleDateString(
              undefined,
              {
                month: 'short',
                day: 'numeric',
                year: 'numeric',
              }
            );

            return (
              <div
                key={session.id}
                className="radar-card p-5 flex flex-col justify-between hover:border-border-active transition-colors space-y-4"
              >
                <div className="space-y-2.5">
                  <div className="flex items-center justify-between gap-2">
                    <Badge type="scope" value={session.scope} size="sm" />
                    <Badge type="job" value={jobStatus} size="sm" />
                  </div>

                  <div>
                    <Link
                      to={`/research/${session.id}`}
                      className="font-heading font-semibold text-base text-text-primary hover:text-accent transition-colors line-clamp-1"
                    >
                      {session.target_name}
                    </Link>
                    <p className="text-xs text-text-secondary line-clamp-2 mt-1">
                      {session.meeting_context || 'No specific meeting objective provided.'}
                    </p>
                  </div>
                </div>

                <div className="pt-3 border-t border-border/40 flex items-center justify-between text-xs font-mono text-text-muted">
                  <div className="flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5 text-accent" />
                    <span>{updatedDate}</span>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => handleDelete(session.id, session.target_name)}
                      className="p-1 text-text-muted hover:text-status-danger transition-colors"
                      title="Delete Session"
                      aria-label="Delete Session"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                    <Link
                      to={`/research/${session.id}`}
                      className="radar-button-secondary text-xs py-1 px-2.5"
                    >
                      <span>Open</span>
                      <ArrowUpRight className="w-3 h-3 text-accent" />
                    </Link>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

