import React from 'react';
import { LucideIcon, Search } from 'lucide-react';

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon: Icon = Search,
  title,
  description,
  actionLabel,
  onAction,
  className = '',
}) => {
  return (
    <div
      className={`radar-card p-10 flex flex-col items-center justify-center text-center max-w-lg mx-auto ${className}`}
    >
      <div className="w-12 h-12 rounded-full bg-bg-elevated border border-border flex items-center justify-center text-text-muted mb-4">
        <Icon className="w-6 h-6 text-accent" />
      </div>
      <h3 className="font-heading font-semibold text-lg text-text-primary mb-2">
        {title}
      </h3>
      <p className="text-sm text-text-secondary leading-relaxed mb-6 max-w-md">
        {description}
      </p>
      {actionLabel && onAction && (
        <button
          type="button"
          onClick={onAction}
          className="radar-button-primary text-sm"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
};

