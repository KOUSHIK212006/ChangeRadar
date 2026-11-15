import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TalkingPointTester } from '../components/research/TalkingPointTester';
import { StressTestResult } from '../types/research';

const queryClient = new QueryClient();

const mockInitialResults: StressTestResult = {
  points: [
    {
      original_point: 'Acme Corp achieved 20% revenue growth in Q3.',
      extracted_claims: ['Acme Corp Q3 revenue grew 20%'],
      assessments: [
        {
          claim_id: 'clm-004',
          text: 'Acme Corp achieved 20% revenue growth in Q3.',
          assessment: 'CONTRADICTED',
          assessment_rationale:
            'Financial Times reports actual revenue growth was 14%, contradicting 20%.',
          evidence: [
            {
              evidence_id: 'ev-004a',
              excerpt: 'Revenue grew 14% year-over-year.',
              source_id: 'src-2',
              relevance: 'CONTRADICTING',
            },
          ],
          source_doc_count: 1,
          independent_origin_count: 1,
          volatility: 'LOW',
          is_stale: false,
          llm_confidence: 0.93,
        },
      ],
      suggested_wording:
        'Acme Corp reported 14% YoY growth in Q3, falling short of market expectations.',
      needs_more_research: false,
    },
  ],
};

describe('TalkingPointTester Component', () => {
  it('renders talking points stress test interface with initial results', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <TalkingPointTester sessionId="sess-001" initialResults={mockInitialResults} />
      </QueryClientProvider>
    );

    expect(screen.getByText(/Talking-Point Stress Test/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Acme Corp achieved 20% revenue growth in Q3/i)
    ).toBeInTheDocument();
    expect(screen.getByText('Contradicted')).toBeInTheDocument();
    expect(
      screen.getByText(/Acme Corp reported 14% YoY growth in Q3/i)
    ).toBeInTheDocument();
  });

  it('allows user to enter new talking points and submit', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <TalkingPointTester sessionId="sess-001" initialResults={null} />
      </QueryClientProvider>
    );

    const textarea = screen.getByLabelText(/Enter Planned Talking Points/i);
    fireEvent.change(textarea, {
      target: { value: 'Acme expanded to Singapore in Q1 2025.' },
    });

    expect(textarea).toHaveValue('Acme expanded to Singapore in Q1 2025.');
    const submitBtn = screen.getByRole('button', { name: /Run Stress Test/i });
    expect(submitBtn).not.toBeDisabled();
  });
});
