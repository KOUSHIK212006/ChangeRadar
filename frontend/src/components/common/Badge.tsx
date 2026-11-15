import React from 'react';
import {
  EvidenceVerificationStatus,
  ResearchJobStatus,
  EventLifecycle,
  ClaimVolatility,
  OwnershipScope,
} from '../../types/research';
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  HelpCircle,
  Clock,
  FileQuestion,
  Loader2,
  Lock,
  Users,
} from 'lucide-react';

type BadgeType =
  | 'evidence'
  | 'job'
  | 'lifecycle'
  | 'volatility'
  | 'scope'
  | 'generic';

interface BadgeProps {
  type?: BadgeType;
  value: string;
  label?: string;
  size?: 'sm' | 'md';
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  type = 'generic',
  value,
  label,
  size = 'md',
  className = '',
}) => {
  const sizeClasses =
    size === 'sm'
      ? 'text-[11px] px-2 py-0.5 gap-1'
      : 'text-xs px-2.5 py-1 gap-1.5';

  // Evidence Status Styling
  if (type === 'evidence') {
    const status = value as EvidenceVerificationStatus;
    switch (status) {
      case 'SUPPORTED':
        return (
          <span
            className={`inline-flex items-center font-medium rounded-full bg-[#182B22] text-[#65B891] border border-[#2D5A43] ${sizeClasses} ${className}`}
            title="Claim is directly backed by retrieved primary evidence"
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>{label || 'Supported'}</span>
          </span>
        );
      case 'PARTIALLY_SUPPORTED':
        return (
          <span
            className={`inline-flex items-center font-medium rounded-full bg-[#2F2718] text-[#E5B45C] border border-[#685227] ${sizeClasses} ${className}`}
            title="Claim has partial evidence but lacks complete factual alignment"
          >
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>{label || 'Partially Supported'}</span>
          </span>
        );
      case 'CONTRADICTED':
        return (
          <span
            className={`inline-flex items-center font-medium rounded-full bg-[#341814] text-[#E45B3F] border border-[#782D1E] ${sizeClasses} ${className}`}
            title="Direct evidence refutes or contradicts this claim"
          >
            <XCircle className="w-3.5 h-3.5" />
            <span>{label || 'Contradicted'}</span>
          </span>
        );
      case 'INSUFFICIENT':
        return (
          <span
            className={`inline-flex items-center font-medium rounded-full bg-[#242321] text-[#A6A096] border border-[#393632] ${sizeClasses} ${className}`}
            title="Retrieved sources lack enough detail to assess claim"
          >
            <HelpCircle className="w-3.5 h-3.5" />
            <span>{label || 'Insufficient Evidence'}</span>
          </span>
        );
      case 'OUTDATED':
        return (
          <span
            className={`inline-flex items-center font-medium rounded-full bg-[#2F2718] text-[#E5B45C] border border-[#685227] ${sizeClasses} ${className}`}
            title="Claim was true at an earlier point but superseded by newer developments"
          >
            <Clock className="w-3.5 h-3.5" />
            <span>{label || 'Outdated / Stale'}</span>
          </span>
        );
      case 'UNVERIFIABLE':
      default:
        return (
          <span
            className={`inline-flex items-center font-medium rounded-full bg-[#222120] text-[#77736B] border border-[#393632] ${sizeClasses} ${className}`}
            title="Subject matter cannot be verified from public sources"
          >
            <FileQuestion className="w-3.5 h-3.5" />
            <span>{label || 'Unverifiable'}</span>
          </span>
        );
    }
  }

  // Job Status Styling
  if (type === 'job') {
    const jobStatus = value as ResearchJobStatus;
    switch (jobStatus) {
      case 'COMPLETED':
        return (
          <span
            className={`inline-flex items-center font-medium rounded-full bg-[#182B22] text-[#65B891] border border-[#2D5A43] ${sizeClasses} ${className}`}
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>{label || 'Completed'}</span>
          </span>
        );
      case 'RUNNING':
        return (
          <span
            className={`inline-flex items-center font-medium rounded-full bg-[#341814] text-[#E45B3F] border border-[#782D1E] ${sizeClasses} ${className}`}
          >
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            <span>{label || 'Running'}</span>
          </span>
        );
      case 'PARTIAL':
        return (
          <span
            className={`inline-flex items-center font-medium rounded-full bg-[#2F2718] text-[#E5B45C] border border-[#685227] ${sizeClasses} ${className}`}
          >
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>{label || 'Partial Results'}</span>
          </span>
        );
      case 'FAILED':
        return (
          <span
            className={`inline-flex items-center font-medium rounded-full bg-[#341814] text-[#E45B3F] border border-[#782D1E] ${sizeClasses} ${className}`}
          >
            <XCircle className="w-3.5 h-3.5" />
            <span>{label || 'Failed'}</span>
          </span>
        );
      case 'QUEUED':
      default:
        return (
          <span
            className={`inline-flex items-center font-medium rounded-full bg-[#242321] text-[#A6A096] border border-[#393632] ${sizeClasses} ${className}`}
          >
            <Clock className="w-3.5 h-3.5" />
            <span>{label || 'Queued'}</span>
          </span>
        );
    }
  }

  // Event Lifecycle Styling
  if (type === 'lifecycle') {
    const lifecycle = value as EventLifecycle;
    switch (lifecycle) {
      case 'NEW':
        return (
          <span
            className={`inline-flex items-center font-medium rounded-full bg-[#341814] text-[#E45B3F] border border-[#782D1E] ${sizeClasses} ${className}`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-[#E45B3F]" />
            <span>{label || 'New Development'}</span>
          </span>
        );
      case 'DEVELOPING':
        return (
          <span
            className={`inline-flex items-center font-medium rounded-full bg-[#2F2718] text-[#E5B45C] border border-[#685227] ${sizeClasses} ${className}`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-[#E5B45C] animate-pulse" />
            <span>{label || 'Developing'}</span>
          </span>
        );
      case 'UPDATED':
        return (
          <span
            className={`inline-flex items-center font-medium rounded-full bg-[#1A2633] text-[#83A9D1] border border-[#2E4862] ${sizeClasses} ${className}`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-[#83A9D1]" />
            <span>{label || 'Updated Baseline'}</span>
          </span>
        );
      case 'COMPLETED':
      default:
        return (
          <span
            className={`inline-flex items-center font-medium rounded-full bg-[#242321] text-[#A6A096] border border-[#393632] ${sizeClasses} ${className}`}
          >
            <span>{label || 'Completed'}</span>
          </span>
        );
    }
  }

  // Volatility Styling
  if (type === 'volatility') {
    const vol = value as ClaimVolatility;
    const color =
      vol === 'HIGH'
        ? 'text-[#E45B3F] border-[#782D1E] bg-[#341814]'
        : vol === 'MEDIUM'
        ? 'text-[#E5B45C] border-[#685227] bg-[#2F2718]'
        : 'text-[#65B891] border-[#2D5A43] bg-[#182B22]';
    return (
      <span
        className={`inline-flex items-center font-medium rounded-full ${color} ${sizeClasses} ${className}`}
        title={`Claim Volatility: ${vol}`}
      >
        <span>{label || `${vol} Volatility`}</span>
      </span>
    );
  }

  // Scope Styling
  if (type === 'scope') {
    const scope = value as OwnershipScope;
    return (
      <span
        className={`inline-flex items-center font-medium rounded-full bg-[#242321] text-[#A6A096] border border-[#393632] ${sizeClasses} ${className}`}
      >
        {scope === 'PERSONAL' ? (
          <Lock className="w-3 h-3 text-[#A6A096]" />
        ) : (
          <Users className="w-3 h-3 text-[#83A9D1]" />
        )}
        <span>{label || (scope === 'PERSONAL' ? 'Personal Scope' : 'Workspace Scope')}</span>
      </span>
    );
  }

  // Generic fallback badge
  return (
    <span
      className={`inline-flex items-center font-medium rounded-full bg-[#242321] text-[#A6A096] border border-[#393632] ${sizeClasses} ${className}`}
    >
      <span>{label || value}</span>
    </span>
  );
};

