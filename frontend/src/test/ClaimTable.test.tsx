import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { ClaimTable } from '../components/research/ClaimTable';
import { ExtractedClaim, SourceRecord } from '../types/research';

const mockClaims: ExtractedClaim[] = [
  {
    claim_id: 'clm-001',
    text: 'Acme Corp is establishing a regional headquarters in Singapore.',
    assessment: 'SUPPORTED',
    assessment_rationale: 'Confirmed by official corporate statement.',
    evidence: [
      {
        evidence_id: 'ev-001a',
        excerpt: 'Acme Corp today announced Singapore regional headquarters.',
        source_id: 'src-1',
        relevance: 'SUPPORTING',
      },
    ],
    source_doc_count: 2,
    independent_origin_count: 1,
    volatility: 'LOW',
    is_stale: false,
    llm_confidence: 0.95,
  },
  {
    claim_id: 'clm-004',
    text: 'Acme Corp achieved 20% revenue growth in Q3.',
    assessment: 'CONTRADICTED',
    assessment_rationale: 'Financial Times reports growth was 14%, contradicting 20%.',
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
];

const mockSources: SourceRecord[] = [
  {
    source_id: 'src-1',
    url: 'https://example.com/press',
    canonical_url: 'https://example.com/press',
    title: 'Acme Announcement',
    publisher: 'BusinessWire',
    snippet: 'Acme Corp today announced...',
    published_at: '2024-10-01T07:00:00Z',
    discovered_at: '2024-10-15T14:22:00Z',
    is_syndicated: true,
    syndication_confidence: 0.9,
  },
  {
    source_id: 'src-2',
    url: 'https://ft.com/acme',
    canonical_url: 'https://ft.com/acme',
    title: 'Acme Earnings',
    publisher: 'Financial Times',
    snippet: 'Revenue grew 14%...',
    published_at: '2024-10-10T16:30:00Z',
    discovered_at: '2024-10-15T14:22:00Z',
    is_syndicated: false,
    syndication_confidence: 0.0,
  },
];

describe('ClaimTable Component', () => {
  it('renders atomic claims with their verification status', () => {
    render(<ClaimTable claims={mockClaims} sources={mockSources} />);

    expect(
      screen.getByText(/Acme Corp is establishing a regional headquarters in Singapore/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Acme Corp achieved 20% revenue growth in Q3/i)
    ).toBeInTheDocument();
    expect(screen.getAllByText('Supported').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Contradicted').length).toBeGreaterThan(0);
  });

  it('filters claims by assessment status', () => {
    render(<ClaimTable claims={mockClaims} sources={mockSources} />);

    const select = screen.getByRole('combobox');
    fireEvent.change(select, { target: { value: 'CONTRADICTED' } });

    expect(
      screen.queryByText(/Acme Corp is establishing a regional headquarters in Singapore/i)
    ).not.toBeInTheDocument();
    expect(
      screen.getByText(/Acme Corp achieved 20% revenue growth in Q3/i)
    ).toBeInTheDocument();
  });

  it('searches claims dynamically by text query', () => {
    render(<ClaimTable claims={mockClaims} sources={mockSources} />);

    const input = screen.getByPlaceholderText(/Search atomic claims or rationale.../i);
    fireEvent.change(input, { target: { value: 'Singapore' } });

    expect(
      screen.getByText(/Acme Corp is establishing a regional headquarters in Singapore/i)
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/Acme Corp achieved 20% revenue growth in Q3/i)
    ).not.toBeInTheDocument();
  });
});

