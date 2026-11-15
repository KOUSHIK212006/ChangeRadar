import React from 'react';
import { Loader2 } from 'lucide-react';

interface LoaderProps {
  label?: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const Loader: React.FC<LoaderProps> = ({
  label = 'Loading intelligence...',
  size = 'md',
  className = '',
}) => {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8',
  }[size];

  return (
    <div
      className={`flex flex-col items-center justify-center p-8 gap-3 text-text-secondary ${className}`}
      role="status"
      aria-live="polite"
    >
      <Loader2 className={`${sizeClasses} text-accent animate-spin`} />
      {label && <p className="text-xs font-mono uppercase tracking-wider">{label}</p>}
    </div>
  );
};

export const CardSkeleton: React.FC<{ rows?: number }> = ({ rows = 3 }) => {
  return (
    <div className="radar-card p-5 animate-pulse space-y-4">
      <div className="h-4 bg-bg-elevated rounded w-1/3"></div>
      <div className="space-y-2">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="h-3 bg-bg-elevated rounded w-full"></div>
        ))}
      </div>
      <div className="h-3 bg-bg-elevated rounded w-1/4"></div>
    </div>
  );
};

