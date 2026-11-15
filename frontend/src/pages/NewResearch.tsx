import React from 'react';
import { PageHeader } from '../components/common/PageHeader';
import { ResearchForm } from '../components/research/ResearchForm';

export const NewResearch: React.FC = () => {
  return (
    <div className="space-y-6 animate-fadeIn max-w-4xl mx-auto">
      <PageHeader
        title="Launch New Research Investigation"
        subtitle="Initiate a targeted research run across primary sources, extract verified claims, and establish your review baseline."
        breadcrumbs={[
          { label: 'Overview', href: '/' },
          { label: 'New Research' },
        ]}
      />

      <ResearchForm />
    </div>
  );
};

