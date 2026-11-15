import React from 'react';
import { LucideIcon } from 'lucide-react';

interface StatsCardProps {
  label: string;
  value: number | string;
  helperText?: string;
  icon: LucideIcon;
  variant?: 'default' | 'accent' | 'warning' | 'success';
}

export const StatsCard: React.FC<StatsCardProps> = ({
  label,
  value,
  helperText,
  icon: Icon,
  variant = 'default',
}) => {
  const iconColors = {
    default: 'text-text-secondary bg-bg-elevated border-border',
    accent: 'text-accent bg-accent/10 border-accent/30',
    warning: 'text-status-warning bg-status-warning/10 border-status-warning/30',
    success: 'text-status-success bg-status-success/10 border-status-success/30',
  }[variant];

  return (
    <div className="radar-card p-5 flex flex-col justify-between">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-mono uppercase tracking-wider text-text-muted">
          {label}
        </span>
        <div
          className={`w-8 h-8 rounded-lg border flex items-center justify-center ${iconColors}`}
        >
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <div className="space-y-1">
        <span className="font-heading font-bold text-2xl md:text-3xl text-text-primary tracking-tight">
          {value}
        </span>
        {helperText && (
          <p className="text-xs text-text-secondary leading-normal">
            {helperText}
          </p>
        )}
      </div>
    </div>
  );
};

