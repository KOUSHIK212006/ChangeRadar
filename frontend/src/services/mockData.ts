import {
  ResearchSession,
  IntelligenceResult,
  DashboardMetrics,
} from '../types/research';

export const MOCK_INTELLIGENCE_RESULT_ACME: IntelligenceResult = {
  session_id: 'sess-001',
  job_id: 'job-001',
  status: 'COMPLETED',
  executive_summary:
    'Acme Corp announced an APAC regional headquarters in Singapore (Q1 2025 launch), confirmed by Reuters and official press releases (1 shared origin). Q3 revenue grew 14% YoY, directly contradicting unverified claims of 20% growth. CFO resigned citing personal reasons with an interim appointment in place; rumors of a permanent replacement remain unsupported.',
  sources: [
    {
      source_id: 'src-a1b2c3d4',
      url: 'https://www.reuters.com/business/acme-corp-apac-expansion-2024-10-01',
      canonical_url: 'https://www.reuters.com/business/acme-corp-apac-expansion-2024-10-01',
      title: 'Acme Corp announces APAC expansion with Singapore hub',
      publisher: 'Reuters',
      snippet:
        'Acme Corp announced plans to establish a regional headquarters in Singapore as part of a broader push into Asia-Pacific markets, targeting a 2025 launch.',
      published_at: '2024-10-01T09:00:00Z',
      discovered_at: '2024-10-15T14:22:00Z',
      is_syndicated: false,
      syndication_confidence: 0.0,
    },
    {
      source_id: 'src-e5f6g7h8',
      url: 'https://www.businesswire.com/news/acme-corp-apac-press-release-2024-10-01',
      canonical_url: 'https://www.businesswire.com/news/acme-corp-apac-press-release-2024-10-01',
      title: 'Acme Corp to Open Singapore Regional HQ — Official Press Release',
      publisher: 'BusinessWire',
      snippet:
        'Acme Corp (NASDAQ: ACME) today announced the establishment of its Asia-Pacific regional headquarters in Singapore, effective Q1 2025.',
      published_at: '2024-10-01T07:00:00Z',
      discovered_at: '2024-10-15T14:22:05Z',
      is_syndicated: true,
      syndication_confidence: 0.91,
    },
    {
      source_id: 'src-i9j0k1l2',
      url: 'https://www.ft.com/content/acme-corp-q3-results-2024',
      canonical_url: 'https://www.ft.com/content/acme-corp-q3-results-2024',
      title: 'Acme Corp Q3 results: revenue up 14% as margins compress',
      publisher: 'Financial Times',
      snippet:
        'Acme Corp reported Q3 revenue growth of 14% year-over-year, falling short of analyst expectations of 18%, while operating margins declined from 22% to 19%.',
      published_at: '2024-10-10T16:30:00Z',
      discovered_at: '2024-10-15T14:22:10Z',
      is_syndicated: false,
      syndication_confidence: 0.0,
    },
    {
      source_id: 'src-m3n4o5p6',
      url: 'https://www.bloomberg.com/news/acme-corp-cfo-departure-2024-09-28',
      canonical_url: 'https://www.bloomberg.com/news/acme-corp-cfo-departure-2024-09-28',
      title: 'Acme Corp CFO departs amid strategic review',
      publisher: 'Bloomberg',
      snippet:
        "Acme Corp's Chief Financial Officer resigned last week, the company confirmed, citing personal reasons. An interim CFO has been appointed while a search is underway.",
      published_at: '2024-09-28T11:00:00Z',
      discovered_at: '2024-10-15T14:22:15Z',
      is_syndicated: false,
      syndication_confidence: 0.0,
    },
  ],
  origins: [
    {
      origin_id: 'org-press001',
      label: 'Acme Corp Official Press Release (APAC Announcement)',
      source_ids: ['src-a1b2c3d4', 'src-e5f6g7h8'],
      is_independent: false,
      independence_confidence: 0.88,
    },
    {
      origin_id: 'org-ft001',
      label: 'Financial Times (independent investigative reporting)',
      source_ids: ['src-i9j0k1l2'],
      is_independent: true,
      independence_confidence: 0.95,
    },
    {
      origin_id: 'org-bbg001',
      label: 'Bloomberg (independent corporate journalism)',
      source_ids: ['src-m3n4o5p6'],
      is_independent: true,
      independence_confidence: 0.95,
    },
  ],
  events: [
    {
      event_id: 'evt-apac01',
      title: 'Acme Corp announces APAC regional headquarters in Singapore',
      description:
        'Acme Corp announced plans to establish a regional headquarters in Singapore targeting a Q1 2025 launch, as part of a broader Asia-Pacific expansion strategy.',
      lifecycle_status: 'NEW',
      is_disputed: false,
      is_uncertain: false,
      event_at: '2024-10-01T07:00:00Z',
      published_at: '2024-10-01T07:00:00Z',
      discovered_at: '2024-10-15T14:22:05Z',
      source_ids: ['src-a1b2c3d4', 'src-e5f6g7h8'],
      origin_ids: ['org-press001'],
      claim_ids: ['clm-001', 'clm-002'],
    },
    {
      event_id: 'evt-q3rev01',
      title: 'Acme Corp Q3 revenue grows 14%, missing consensus expectations',
      description:
        'Acme Corp reported Q3 revenue growth of 14% year-over-year, missing analyst consensus of 18%. Operating margins contracted from 22% to 19%.',
      lifecycle_status: 'NEW',
      is_disputed: false,
      is_uncertain: false,
      event_at: '2024-10-10T00:00:00Z',
      published_at: '2024-10-10T16:30:00Z',
      discovered_at: '2024-10-15T14:22:10Z',
      source_ids: ['src-i9j0k1l2'],
      origin_ids: ['org-ft001'],
      claim_ids: ['clm-003', 'clm-004'],
    },
    {
      event_id: 'evt-cfo01',
      title: 'Acme Corp CFO resigns; interim successor appointed',
      description:
        "Acme Corp's CFO resigned citing personal reasons. An interim appointment was confirmed while an executive search is underway.",
      lifecycle_status: 'UPDATED',
      is_disputed: false,
      is_uncertain: false,
      event_at: '2024-09-28T00:00:00Z',
      published_at: '2024-09-28T11:00:00Z',
      discovered_at: '2024-10-15T14:22:15Z',
      source_ids: ['src-m3n4o5p6'],
      origin_ids: ['org-bbg001'],
      claim_ids: ['clm-005', 'clm-006'],
    },
  ],
  event_versions: [
    {
      version_id: 'ver-cfo01-v1',
      event_id: 'evt-cfo01',
      description: 'Initial market reports indicated CFO abruptly stepped back.',
      lifecycle_status: 'NEW',
      source_ids: ['src-m3n4o5p6'],
      recorded_at: '2024-09-28T11:00:00Z',
    },
    {
      version_id: 'ver-cfo01-v2',
      event_id: 'evt-cfo01',
      description: 'Company acknowledged resignation; interim CFO appointed.',
      lifecycle_status: 'UPDATED',
      source_ids: ['src-m3n4o5p6'],
      recorded_at: '2024-10-02T10:00:00Z',
    },
  ],
  claims: [
    {
      claim_id: 'clm-001',
      text: 'Acme Corp is establishing a regional headquarters in Singapore.',
      assessment: 'SUPPORTED',
      assessment_rationale:
        'Confirmed by official corporate statement and reported by Reuters.',
      evidence: [
        {
          evidence_id: 'ev-001a',
          excerpt:
            'Acme Corp (NASDAQ: ACME) today announced the establishment of its Asia-Pacific regional headquarters in Singapore, effective Q1 2025.',
          source_id: 'src-e5f6g7h8',
          relevance: 'SUPPORTING',
        },
      ],
      source_doc_count: 2,
      independent_origin_count: 1,
      volatility: 'LOW',
      is_stale: false,
      llm_confidence: 0.97,
    },
    {
      claim_id: 'clm-002',
      text: 'The Singapore APAC hub is scheduled to open in Q1 2025.',
      assessment: 'SUPPORTED',
      assessment_rationale:
        'Exact timeline specified directly in company announcement.',
      evidence: [
        {
          evidence_id: 'ev-002a',
          excerpt: '...effective Q1 2025.',
          source_id: 'src-e5f6g7h8',
          relevance: 'SUPPORTING',
        },
      ],
      source_doc_count: 2,
      independent_origin_count: 1,
      volatility: 'MEDIUM',
      is_stale: false,
      llm_confidence: 0.94,
    },
    {
      claim_id: 'clm-003',
      text: 'Acme Corp Q3 revenue grew 14% year-over-year.',
      assessment: 'SUPPORTED',
      assessment_rationale: 'Reported directly by Financial Times based on quarterly earnings filing.',
      evidence: [
        {
          evidence_id: 'ev-003a',
          excerpt:
            'Acme Corp reported Q3 revenue growth of 14% year-over-year, falling short of analyst expectations...',
          source_id: 'src-i9j0k1l2',
          relevance: 'SUPPORTING',
        },
      ],
      source_doc_count: 1,
      independent_origin_count: 1,
      volatility: 'LOW',
      is_stale: false,
      llm_confidence: 0.96,
    },
    {
      claim_id: 'clm-004',
      text: 'Acme Corp achieved 20% revenue growth in Q3.',
      assessment: 'CONTRADICTED',
      assessment_rationale:
        'Financial Times reports actual revenue growth was 14%, contradicting the 20% assertion.',
      evidence: [
        {
          evidence_id: 'ev-004a',
          excerpt:
            'Acme Corp reported Q3 revenue growth of 14% year-over-year, falling short of analyst expectations of 18%.',
          source_id: 'src-i9j0k1l2',
          relevance: 'CONTRADICTING',
        },
      ],
      source_doc_count: 1,
      independent_origin_count: 1,
      volatility: 'LOW',
      is_stale: false,
      llm_confidence: 0.93,
    },
    {
      claim_id: 'clm-005',
      text: "Acme Corp's Chief Financial Officer has resigned.",
      assessment: 'SUPPORTED',
      assessment_rationale: 'Confirmed by Bloomberg; company verified departure.',
      evidence: [
        {
          evidence_id: 'ev-005a',
          excerpt:
            "Acme Corp's Chief Financial Officer resigned last week, the company confirmed, citing personal reasons.",
          source_id: 'src-m3n4o5p6',
          relevance: 'SUPPORTING',
        },
      ],
      source_doc_count: 1,
      independent_origin_count: 1,
      volatility: 'LOW',
      is_stale: false,
      llm_confidence: 0.98,
    },
    {
      claim_id: 'clm-006',
      text: 'A permanent CFO successor has been selected and finalized.',
      assessment: 'INSUFFICIENT',
      assessment_rationale:
        'Evidence only confirms an interim role; search remains active with no successor named.',
      evidence: [
        {
          evidence_id: 'ev-006a',
          excerpt: 'An interim CFO has been appointed while a search is underway.',
          source_id: 'src-m3n4o5p6',
          relevance: 'CONTRADICTING',
        },
      ],
      source_doc_count: 1,
      independent_origin_count: 1,
      volatility: 'HIGH',
      is_stale: false,
      llm_confidence: 0.82,
    },
  ],
  coverage: {
    planned_searches: 5,
    executed_searches: 5,
    failed_searches: 0,
    time_window_days: 30,
    source_types_found: ['news', 'press_release'],
    origin_diversity_score: 0.67,
    gaps: [
      'No official regulatory SEC 10-Q filing parsed directly for the current quarter',
      'No primary customer commentary or regional partner feedback yet available',
    ],
    warnings: [
      'Singapore expansion coverage is syndicated from 1 corporate press release origin; do not treat as multiple independent verifications.',
    ],
  },
  delta: {
    new_events: ['evt-apac01', 'evt-q3rev01'],
    updated_events: ['evt-cfo01'],
    new_evidence_for_claims: ['clm-003', 'clm-004'],
    changed_assessments: ['clm-006'],
    no_material_change: false,
    comparison_incomplete: false,
    incompleteness_reason: null,
  },
  stress_test: {
    points: [
      {
        original_point: 'Acme Corp is aggressively expanding into the APAC market with high momentum.',
        extracted_claims: ['Acme Corp is expanding into the APAC market'],
        assessments: [
          {
            claim_id: 'clm-001',
            text: 'Acme Corp is establishing a regional headquarters in Singapore.',
            assessment: 'SUPPORTED',
            assessment_rationale:
              'Confirmed by official corporate statement and reported by Reuters.',
            evidence: [
              {
                evidence_id: 'ev-001a',
                excerpt:
                  'Acme Corp (NASDAQ: ACME) today announced the establishment of its Asia-Pacific regional headquarters in Singapore, effective Q1 2025.',
                source_id: 'src-e5f6g7h8',
                relevance: 'SUPPORTING',
              },
            ],
            source_doc_count: 2,
            independent_origin_count: 1,
            volatility: 'LOW',
            is_stale: false,
            llm_confidence: 0.97,
          },
        ],
        suggested_wording:
          'Acme Corp has announced plans for a regional headquarters in Singapore targeting Q1 2025, though execution has not yet commenced.',
        needs_more_research: false,
      },
      {
        original_point: 'Their revenue surged by 20% year-over-year in Q3.',
        extracted_claims: ['Acme Corp Q3 revenue grew 20% year-over-year'],
        assessments: [
          {
            claim_id: 'clm-004',
            text: 'Acme Corp achieved 20% revenue growth in Q3.',
            assessment: 'CONTRADICTED',
            assessment_rationale:
              'Financial Times reports actual revenue growth was 14%, contradicting the 20% assertion.',
            evidence: [
              {
                evidence_id: 'ev-004a',
                excerpt:
                  'Acme Corp reported Q3 revenue growth of 14% year-over-year, falling short of analyst expectations of 18%.',
                source_id: 'src-i9j0k1l2',
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
          'Acme Corp reported 14% YoY revenue growth in Q3, falling short of the 18% analyst consensus, while margins compressed to 19%.',
        needs_more_research: false,
      },
      {
        original_point: 'They already announced a permanent CFO successor to stabilize leadership.',
        extracted_claims: ['A permanent CFO successor has been selected and finalized.'],
        assessments: [
          {
            claim_id: 'clm-006',
            text: 'A permanent CFO successor has been selected and finalized.',
            assessment: 'INSUFFICIENT',
            assessment_rationale:
              'Evidence only confirms an interim role; search remains active with no successor named.',
            evidence: [
              {
                evidence_id: 'ev-006a',
                excerpt: 'An interim CFO has been appointed while a search is underway.',
                source_id: 'src-m3n4o5p6',
                relevance: 'CONTRADICTING',
              },
            ],
            source_doc_count: 1,
            independent_origin_count: 1,
            volatility: 'HIGH',
            is_stale: false,
            llm_confidence: 0.82,
          },
        ],
        suggested_wording:
          'Acme Corp has appointed an interim CFO following the previous executive’s resignation, while the executive search for a permanent successor is ongoing.',
        needs_more_research: true,
      },
    ],
  },
  warnings: [],
  provider_metadata: {
    search_provider: 'Tavily / Verified Fixture',
    llm_model: 'Gemini Pro 1.5',
    run_at: '2024-10-15T14:22:00Z',
    baseline_id: 'res-baseline-202409',
  },
};

export const MOCK_SESSIONS: ResearchSession[] = [
  {
    id: 'sess-001',
    title: 'Acme Corp — Pre-Partnership Briefing',
    target_name: 'Acme Corp',
    target_type: 'company',
    meeting_context: 'Commercial partnership negotiation with VP of Global Strategy',
    time_window_days: 30,
    research_questions: [
      'What are their recent international expansion moves?',
      'How did their recent financial quarter perform against expectations?',
      'Are there notable leadership transitions?',
    ],
    talking_points: [
      'Acme Corp is aggressively expanding into the APAC market with high momentum.',
      'Their revenue surged by 20% year-over-year in Q3.',
      'They already announced a permanent CFO successor to stabilize leadership.',
    ],
    scope: 'PERSONAL',
    status: 'ACTIVE',
    last_reviewed_at: '2024-09-20T10:00:00Z',
    last_reviewed_result_id: 'res-baseline-202409',
    created_at: '2024-10-15T14:20:00Z',
    updated_at: '2024-10-15T14:25:00Z',
    latest_job: {
      id: 'job-001',
      session_id: 'sess-001',
      status: 'COMPLETED',
      current_stage: 'COMPLETE',
      progress_pct: 100,
      attempt_count: 1,
      error_message: null,
      created_at: '2024-10-15T14:20:05Z',
      updated_at: '2024-10-15T14:24:55Z',
    },
    latest_result: MOCK_INTELLIGENCE_RESULT_ACME,
  },
  {
    id: 'sess-002',
    title: 'Dr. Elena Rostova — Executive Evaluation',
    target_name: 'Dr. Elena Rostova',
    target_type: 'person',
    meeting_context: 'Interviewing for Chief AI Officer position',
    time_window_days: 90,
    research_questions: [
      'Recent publications or patent filings?',
      'Departure circumstances from previous employer?',
      'Public talks or statements regarding safety benchmarks?',
    ],
    talking_points: [
      'She authored the leading 2024 benchmark paper on retrieval evaluation.',
      'Her previous startup was acquired for over $100M.',
    ],
    scope: 'PERSONAL',
    status: 'ACTIVE',
    last_reviewed_at: null,
    last_reviewed_result_id: null,
    created_at: '2024-10-14T09:15:00Z',
    updated_at: '2024-10-14T09:22:00Z',
    latest_job: {
      id: 'job-002',
      session_id: 'sess-002',
      status: 'COMPLETED',
      current_stage: 'COMPLETE',
      progress_pct: 100,
      attempt_count: 1,
      error_message: null,
      created_at: '2024-10-14T09:15:05Z',
      updated_at: '2024-10-14T09:21:40Z',
    },
  },
  {
    id: 'sess-003',
    title: 'BioSynthetix Therapeutics — Clinical Pipeline Scan',
    target_name: 'BioSynthetix Therapeutics',
    target_type: 'topic',
    meeting_context: 'Series B diligence review with scientific advisory board',
    time_window_days: 60,
    research_questions: [
      'Status of Phase 2 oncology trial enrollment?',
      'Any FDA interactions or hold notices?',
    ],
    talking_points: [],
    scope: 'WORKSPACE',
    workspace_id: 'ws-core-team',
    status: 'ACTIVE',
    last_reviewed_at: '2024-09-01T12:00:00Z',
    last_reviewed_result_id: 'res-bio-01',
    created_at: '2024-10-12T16:00:00Z',
    updated_at: '2024-10-12T16:08:00Z',
    latest_job: {
      id: 'job-003',
      session_id: 'sess-003',
      status: 'PARTIAL',
      current_stage: 'COVERAGE_AUDIT',
      progress_pct: 85,
      attempt_count: 2,
      error_message: 'Clinical trial registry crawler rate-limited; partial records retained.',
      created_at: '2024-10-12T16:00:05Z',
      updated_at: '2024-10-12T16:07:30Z',
    },
  },
];

export const MOCK_METRICS: DashboardMetrics = {
  totalSessions: 3,
  newDevelopments: 5,
  supportedClaims: 4,
  evidenceGaps: 3,
  isMockData: true,
};

