import React from 'react';
import { AlertOctagon, RotateCcw } from 'lucide-react';

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  className?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Intelligence Retrieval Failed',
  message = 'An unexpected error occurred while communicating with the platform API.',
  onRetry,
  className = '',
}) => {
  return (
    <div
      className={`radar-card p-8 border-status-danger/40 bg-bg-secondary flex flex-col items-center justify-center text-center max-w-lg mx-auto ${className}`}
      role="alert"
    >
      <div className="w-12 h-12 rounded-full bg-[#341814] border border-[#782D1E] flex items-center justify-center text-status-danger mb-4">
        <AlertOctagon className="w-6 h-6" />
      </div>
      <h3 className="font-heading font-semibold text-lg text-text-primary mb-2">
        {title}
      </h3>
      <p className="text-sm text-text-secondary leading-relaxed mb-6 font-mono text-xs">
        {message}
      </p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="radar-button-secondary text-sm"
        >
          <RotateCcw className="w-4 h-4" />
          <span>Retry Operation</span>
        </button>
      )}
    </div>
  );
};

