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
    'MapmyIndia (C.E. Info Systems Ltd.) served a formal legal notice to Ola Electric alleging breach of a 2021 licensing agreement and reverse-engineering of proprietary mapping APIs to build Ola Maps, corroborated by Forbes India and official regulatory filings. Full-year consolidated revenue reached ₹463.3 crore (+22% YoY) with ~40% EBITDA margins and a ₹1,500 crore open order book, directly contradicting rumors of financial contraction following Ola’s departure. Expansion into automotive ADAS, drone navigation, and 3D digital twins continues to drive enterprise contract momentum.',
  sources: [
    {
      source_id: 'src-mmi01',
      url: 'https://www.forbesindia.com/article/special/mapmyindia-legal-notice-ola-electric-maps/94521/1',
      canonical_url: 'https://www.forbesindia.com/article/special/mapmyindia-legal-notice-ola-electric-maps/94521/1',
      title: 'MapmyIndia serves legal notice to Ola Electric over Ola Maps IP dispute',
      publisher: 'Forbes India',
      snippet:
        'C.E. Info Systems (parent of MapmyIndia) served a formal legal notice to Ola Electric alleging breach of a 2021 client agreement, claiming Ola co-mingled and reverse-engineered proprietary mapping APIs to construct Ola Maps.',
      published_at: '2026-11-08T10:00:00Z',
      discovered_at: '2026-11-18T14:22:00Z',
      is_syndicated: false,
      syndication_confidence: 0.0,
    },
    {
      source_id: 'src-mmi02',
      url: 'https://economictimes.indiatimes.com/tech/technology/ola-refutes-mapmyindia-allegations-as-malicious/articleshow/112108745.cms',
      canonical_url: 'https://economictimes.indiatimes.com/tech/technology/ola-refutes-mapmyindia-allegations-as-malicious/articleshow/112108745.cms',
      title: 'Ola Electric refutes MapmyIndia IP infringement allegations as malicious',
      publisher: 'The Economic Times',
      snippet:
        'Ola Electric strongly denied allegations of data theft, stating that Ola Maps was developed independently using open-source repositories and in-house technology, calling the notice an opportunistic move.',
      published_at: '2026-11-09T07:00:00Z',
      discovered_at: '2026-11-18T14:22:05Z',
      is_syndicated: true,
      syndication_confidence: 0.88,
    },
    {
      source_id: 'src-mmi03',
      url: 'https://www.bseindia.com/xml-data/corpfiling/AttachLive/ceinfost-q2-earnings-disclosure.pdf',
      canonical_url: 'https://www.bseindia.com/xml-data/corpfiling/AttachLive/ceinfost-q2-earnings-disclosure.pdf',
      title: 'C.E. Info Systems Ltd. Audited Financial Statements & Operational Review',
      publisher: 'BSE / NSE Corporate Filings',
      snippet:
        'C.E. Info Systems reported annual consolidated revenue from operations of ₹463.3 crore, up 22% YoY. Profit After Tax (PAT) stood at ₹147.6 crore with an EBITDA margin of 39.5%. Open enterprise order book was reported at ₹1,500 crore.',
      published_at: '2026-11-14T16:30:00Z',
      discovered_at: '2026-11-19T14:22:10Z',
      is_syndicated: false,
      syndication_confidence: 0.0,
    },
    {
      source_id: 'src-mmi04',
      url: 'https://www.tradingview.com/news/mapmyindia-mappls-zoho-arattai-navigation/',
      canonical_url: 'https://www.tradingview.com/news/mapmyindia-mappls-zoho-arattai-navigation/',
      title: 'MapmyIndia Mappls links up with Zoho Arattai & expands ADAS navigation footprint',
      publisher: 'TradingView / Business Standard',
      snippet:
        'MapmyIndia (C.E. Info Systems) announced an enterprise integration with Zoho Arattai for in-chat location navigation, alongside new multi-year agreements with leading automotive OEMs for Level 2+ ADAS high-definition maps and drone logistics.',
      published_at: '2026-11-17T08:35:46Z',
      discovered_at: '2026-11-20T14:22:15Z',
      is_syndicated: false,
      syndication_confidence: 0.0,
    },
  ],
  origins: [
    {
      origin_id: 'org-bse01',
      label: 'C.E. Info Systems Regulatory Disclosures (BSE/NSE Audited Filings)',
      source_ids: ['src-mmi03'],
      is_independent: true,
      independence_confidence: 0.99,
    },
    {
      origin_id: 'org-forbes01',
      label: 'Forbes India (Independent investigative reporting on Ola dispute)',
      source_ids: ['src-mmi01'],
      is_independent: true,
      independence_confidence: 0.95,
    },
    {
      origin_id: 'org-et01',
      label: 'The Economic Times / TradingView (Independent corporate technology journalism)',
      source_ids: ['src-mmi02', 'src-mmi04'],
      is_independent: true,
      independence_confidence: 0.92,
    },
  ],
  events: [
    {
      event_id: 'evt-mmi01',
      title: 'MapmyIndia serves formal legal notice to Ola Electric alleging IP theft in Ola Maps',
      description:
        'C.E. Info Systems served a formal legal notice to Ola Electric alleging breach of a 2021 licensing agreement, asserting that Ola co-mingled and reverse-engineered MapmyIndia proprietary APIs to develop Ola Maps.',
      lifecycle_status: 'NEW',
      is_disputed: true,
      is_uncertain: false,
      event_at: '2026-11-08T10:00:00Z',
      published_at: '2026-11-08T10:00:00Z',
      discovered_at: '2026-11-18T14:22:05Z',
      source_ids: ['src-mmi01', 'src-mmi02'],
      origin_ids: ['org-forbes01'],
      claim_ids: ['clm-001', 'clm-004'],
    },
    {
      event_id: 'evt-mmi02',
      title: 'C.E. Info Systems posts 22% annual revenue growth to ₹463.3 Crore',
      description:
        'MapmyIndia delivered annual consolidated operational revenue of ₹463.3 crore (+22% YoY) and net profit of ₹147.6 crore, maintaining robust ~40% EBITDA margins.',
      lifecycle_status: 'NEW',
      is_disputed: false,
      is_uncertain: false,
      event_at: '2026-11-14T00:00:00Z',
      published_at: '2026-11-14T16:30:00Z',
      discovered_at: '2026-11-19T14:22:10Z',
      source_ids: ['src-mmi03'],
      origin_ids: ['org-bse01'],
      claim_ids: ['clm-002', 'clm-003'],
    },
    {
      event_id: 'evt-mmi03',
      title: 'Enterprise order book surges to ₹1,500 Crore on ADAS & Drone mapping wins',
      description:
        'Company disclosed an open order pipeline of ₹1,500 crore driven by automotive ADAS Level 2+ adoption and digital twin geospatial solutions.',
      lifecycle_status: 'UPDATED',
      is_disputed: false,
      is_uncertain: false,
      event_at: '2026-11-17T08:35:00Z',
      published_at: '2026-11-17T08:35:46Z',
      discovered_at: '2026-11-20T14:22:15Z',
      source_ids: ['src-mmi04'],
      origin_ids: ['org-et01'],
      claim_ids: ['clm-005'],
    },
  ],
  event_versions: [
    {
      version_id: 'ver-mmi01-v1',
      event_id: 'evt-mmi01',
      description: 'Ola Electric announced total migration from Google Maps to in-house Ola Maps.',
      lifecycle_status: 'NEW',
      source_ids: ['src-mmi02'],
      recorded_at: '2026-11-07T11:00:00Z',
    },
    {
      version_id: 'ver-mmi01-v2',
      event_id: 'evt-mmi01',
      description: 'MapmyIndia formally issued legal notice citing breach of 2021 licensing agreement.',
      lifecycle_status: 'UPDATED',
      source_ids: ['src-mmi01'],
      recorded_at: '2026-11-08T10:00:00Z',
    },
  ],
  claims: [
    {
      claim_id: 'clm-001',
      text: 'MapmyIndia served a formal legal notice to Ola Electric alleging breach of their 2021 licensing agreement.',
      assessment: 'SUPPORTED',
      assessment_rationale:
        'Corroborated by investigative reporting in Forbes India, The Economic Times, and confirmed legal correspondence.',
      evidence: [
        {
          evidence_id: 'ev-001a',
          excerpt:
            'C.E. Info Systems (parent of MapmyIndia) served a formal legal notice to Ola Electric alleging breach of a 2021 client agreement, claiming Ola co-mingled and reverse-engineered proprietary mapping APIs to construct Ola Maps.',
          source_id: 'src-mmi01',
          relevance: 'SUPPORTING',
        },
      ],
      source_doc_count: 2,
      independent_origin_count: 2,
      volatility: 'LOW',
      is_stale: false,
      llm_confidence: 0.98,
    },
    {
      claim_id: 'clm-002',
      text: 'MapmyIndia delivered annual operational revenue of ₹463.3 crore, achieving 22% year-on-year growth.',
      assessment: 'SUPPORTED',
      assessment_rationale:
        'Directly documented in official audited regulatory disclosures filed with the BSE and NSE.',
      evidence: [
        {
          evidence_id: 'ev-002a',
          excerpt:
            'C.E. Info Systems reported annual consolidated revenue from operations of ₹463.3 crore, up 22% YoY. Profit After Tax (PAT) stood at ₹147.6 crore with an EBITDA margin of 39.5%.',
          source_id: 'src-mmi03',
          relevance: 'SUPPORTING',
        },
      ],
      source_doc_count: 1,
      independent_origin_count: 1,
      volatility: 'LOW',
      is_stale: false,
      llm_confidence: 0.99,
    },
    {
      claim_id: 'clm-003',
      text: 'MapmyIndia suffered financial decline following Ola Electric’s transition to Ola Maps.',
      assessment: 'CONTRADICTED',
      assessment_rationale:
        'Audited filings confirm revenue grew 22% YoY to ₹463.3 crore with ~40% EBITDA margins and a ₹1,500 crore order book, directly refuting claims of financial decline.',
      evidence: [
        {
          evidence_id: 'ev-003a',
          excerpt:
            'Consolidated revenue from operations grew 22% YoY to ₹463.3 Cr... Open enterprise order book was reported at ₹1,500 crore.',
          source_id: 'src-mmi03',
          relevance: 'CONTRADICTING',
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
      text: 'Ola Electric independently built Ola Maps solely using public open-source data without proprietary MapmyIndia APIs.',
      assessment: 'INSUFFICIENT',
      assessment_rationale:
        'Ola public statements claim independent development, but MapmyIndia has formally submitted specific technical allegations of API caching and reverse engineering.',
      evidence: [
        {
          evidence_id: 'ev-004a',
          excerpt:
            'Ola Electric strongly denied allegations of data theft, stating that Ola Maps was developed independently using open-source repositories...',
          source_id: 'src-mmi02',
          relevance: 'CONTEXTUAL',
        },
      ],
      source_doc_count: 2,
      independent_origin_count: 2,
      volatility: 'HIGH',
      is_stale: false,
      llm_confidence: 0.85,
    },
    {
      claim_id: 'clm-005',
      text: 'MapmyIndia has secured ₹1,500 crore in open enterprise orders across automotive ADAS and drone logistics.',
      assessment: 'SUPPORTED',
      assessment_rationale: 'Confirmed in official investor presentation and corporate releases reported by Business Standard.',
      evidence: [
        {
          evidence_id: 'ev-005a',
          excerpt:
            'MapmyIndia announced new multi-year agreements with leading automotive OEMs for Level 2+ ADAS high-definition maps and enterprise drone logistics navigation.',
          source_id: 'src-mmi04',
          relevance: 'SUPPORTING',
        },
      ],
      source_doc_count: 2,
      independent_origin_count: 2,
      volatility: 'LOW',
      is_stale: false,
      llm_confidence: 0.95,
    },
  ],
  coverage: {
    planned_searches: 5,
    executed_searches: 5,
    failed_searches: 0,
    time_window_days: 14,
    source_types_found: ['regulatory_filing', 'financial_press', 'tech_media'],
    origin_diversity_score: 0.88,
    gaps: [
      'Delhi High Court pre-trial scheduling order details pending publication on court docket',
    ],
    warnings: [
      'Ola statements regarding open-source development originate solely from Ola PR and have not been independently audited.',
    ],
  },
  delta: {
    new_events: ['evt-mmi02', 'evt-mmi03'],
    updated_events: ['evt-mmi01'],
    new_evidence_for_claims: ['clm-002', 'clm-003'],
    changed_assessments: [],
    no_material_change: false,
    comparison_incomplete: false,
    incompleteness_reason: null,
  },
  stress_test: {
    points: [
      {
        original_point: 'MapmyIndia served a formal legal notice to Ola Electric alleging breach of their mapping agreement.',
        extracted_claims: ['MapmyIndia served legal notice to Ola Electric regarding Ola Maps IP dispute'],
        assessments: [
          {
            claim_id: 'clm-001',
            text: 'MapmyIndia served a formal legal notice to Ola Electric alleging breach of their 2021 licensing agreement.',
            assessment: 'SUPPORTED',
            assessment_rationale:
              'Corroborated by investigative reporting in Forbes India, The Economic Times, and confirmed legal correspondence.',
            evidence: [
              {
                evidence_id: 'ev-001a',
                excerpt:
                  'C.E. Info Systems (parent of MapmyIndia) served a formal legal notice to Ola Electric alleging breach of a 2021 client agreement...',
                source_id: 'src-mmi01',
                relevance: 'SUPPORTING',
              },
            ],
            source_doc_count: 2,
            independent_origin_count: 2,
            volatility: 'LOW',
            is_stale: false,
            llm_confidence: 0.98,
          },
        ],
        suggested_wording:
          'MapmyIndia has issued a formal legal notice to Ola Electric alleging breach of their 2021 client licensing agreement and unauthorized API data reverse-engineering.',
        needs_more_research: false,
      },
      {
        original_point: 'MapmyIndia suffered severe financial decline after Ola launched Ola Maps.',
        extracted_claims: ['MapmyIndia revenue declined following Ola departure'],
        assessments: [
          {
            claim_id: 'clm-003',
            text: 'MapmyIndia suffered financial decline following Ola Electric’s transition to Ola Maps.',
            assessment: 'CONTRADICTED',
            assessment_rationale:
              'Audited filings confirm revenue grew 22% YoY to ₹463.3 crore with ~40% EBITDA margins and a ₹1,500 crore order book, directly refuting claims of financial decline.',
            evidence: [
              {
                evidence_id: 'ev-003a',
                excerpt:
                  'Consolidated revenue from operations grew 22% YoY to ₹463.3 Cr... Open enterprise order book was reported at ₹1,500 crore.',
                source_id: 'src-mmi03',
                relevance: 'CONTRADICTING',
              },
            ],
            source_doc_count: 1,
            independent_origin_count: 1,
            volatility: 'LOW',
            is_stale: false,
            llm_confidence: 0.96,
          },
        ],
        suggested_wording:
          'Contrary to assumptions of financial contraction, MapmyIndia reported a 22% YoY revenue growth to ₹463.3 crore with ~40% EBITDA margins, underpinned by an open order book of ₹1,500 crore.',
        needs_more_research: false,
      },
    ],
  },
  warnings: [],
  provider_metadata: {
    search_provider: 'Tavily / Verified Fixture',
    llm_model: 'Gemini 1.5 Flash via Bifrost',
    run_at: '2026-11-21T14:22:00Z',
    baseline_id: 'res-baseline-202611',
  },
};

export const MOCK_SESSIONS: ResearchSession[] = [
  {
    id: 'sess-001',
    title: 'MapmyIndia (C.E. Info Systems) — Pre-Partnership Briefing',
    target_name: 'MapmyIndia (C.E. Info Systems)',
    target_type: 'company',
    meeting_context: 'Strategic enterprise partnership & quarterly diligence review with Leadership',
    time_window_days: 14,
    research_questions: [
      'What is the verified legal and technical status of the Ola Maps intellectual property dispute?',
      'How did audited full-year and recent quarterly revenues perform against market expectations?',
      'What are their confirmed new contracts across ADAS and drone logistics?',
    ],
    talking_points: [
      'MapmyIndia served a formal legal notice to Ola Electric alleging breach of their mapping agreement.',
      'MapmyIndia suffered severe financial decline after Ola launched Ola Maps.',
    ],
    scope: 'PERSONAL',
    status: 'ACTIVE',
    last_reviewed_at: '2026-11-07T10:00:00Z',
    last_reviewed_result_id: 'res-baseline-202611',
    created_at: '2026-11-20T14:20:00Z',
    updated_at: '2026-11-21T14:25:00Z',
    latest_job: {
      id: 'job-001',
      session_id: 'sess-001',
      status: 'COMPLETED',
      current_stage: 'COMPLETE',
      progress_pct: 100,
      attempt_count: 1,
      error_message: null,
      created_at: '2026-11-21T14:20:05Z',
      updated_at: '2026-11-21T14:24:55Z',
    },
    latest_result: MOCK_INTELLIGENCE_RESULT_ACME,
  },
  {
    id: 'sess-002',
    title: 'Kaynes Technology India — OSAT Semiconductor Plant Diligence',
    target_name: 'Kaynes Technology India',
    target_type: 'company',
    meeting_context: 'Commercial diligence review on Sanand semiconductor plant & ESDM growth',
    time_window_days: 14,
    research_questions: [
      'What is the status of the Union Cabinet approval for the Sanand OSAT plant?',
      'What was the recent quarterly revenue growth in automotive vs industrial ESDM?',
    ],
    talking_points: [
      'Kaynes received Union Cabinet approval for its ₹3,307 crore semiconductor facility in Sanand.',
    ],
    scope: 'WORKSPACE',
    status: 'ACTIVE',
    last_reviewed_at: null,
    last_reviewed_result_id: null,
    created_at: '2026-11-19T09:15:00Z',
    updated_at: '2026-11-19T09:22:00Z',
    latest_job: {
      id: 'job-002',
      session_id: 'sess-002',
      status: 'COMPLETED',
      current_stage: 'COMPLETE',
      progress_pct: 100,
      attempt_count: 1,
      error_message: null,
      created_at: '2026-11-19T09:15:05Z',
      updated_at: '2026-11-19T09:21:40Z',
    },
  },
  {
    id: 'sess-003',
    title: 'Swiggy India — Quick Commerce & Logistics Diligence',
    target_name: 'Swiggy India',
    target_type: 'company',
    meeting_context: 'Logistics technology evaluation and dark-store unit economics review',
    time_window_days: 14,
    research_questions: [
      'What are the confirmed Instamart dark store expansion milestones?',
      'How do average order value and contribution margins compare with peers?',
    ],
    talking_points: [],
    scope: 'WORKSPACE',
    workspace_id: 'ws-core-team',
    status: 'ACTIVE',
    last_reviewed_at: '2026-11-07T12:00:00Z',
    last_reviewed_result_id: 'res-swiggy-202611',
    created_at: '2026-11-18T16:00:00Z',
    updated_at: '2026-11-18T16:08:00Z',
    latest_job: {
      id: 'job-003',
      session_id: 'sess-003',
      status: 'COMPLETED',
      current_stage: 'COMPLETE',
      progress_pct: 100,
      attempt_count: 1,
      error_message: null,
      created_at: '2026-11-18T16:00:05Z',
      updated_at: '2026-11-18T16:07:30Z',
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

