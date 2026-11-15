import React from 'react';
import { useNavigate } from 'react-router-dom';
import { EmptyState } from '../components/common/EmptyState';
import { AlertCircle } from 'lucide-react';

export const NotFound: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="py-16">
      <EmptyState
        icon={AlertCircle}
        title="404 — Dossier Not Found"
        description="The requested research route or investigation page does not exist or has been removed."
        actionLabel="Return to Overview"
        onAction={() => navigate('/')}
      />
    </div>
  );
};

