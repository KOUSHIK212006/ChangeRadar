# ChangeRadar Frontend Integration Document

This document records the cross-functional contracts and alignment between:
- **Koushik** (Frontend Architecture & UI/UX)
- **Surjith** (AI Research & Intelligence Engine)
- **Krishank** (Backend Platform & Database Infrastructure)

---

## 1. Ownership & Boundary Constraints
- Every `ResearchSession` is strictly bounded by ownership scope:
  - `PERSONAL`: `owner_user_id` set, `workspace_id` is null. Private to the user.
  - `WORKSPACE`: `workspace_id` set, `owner_user_id` is null. Shared within workspace.
- The UI strictly enforces this separation through separate scope selection and view filtering.
- Client-side checks are informative; Krishank's FastAPI backend enforces authorization on all endpoints.

---

## 2. Shared Intelligence Engine Schemas (Surjith)
All frontend data models in `src/types/research.ts` align 1:1 with `backend/intelligence/contracts.py`:

### Evidence Verification Status Enum
- `SUPPORTED`: Claim directly corroborated by primary sources.
- `PARTIALLY_SUPPORTED`: Corroborated in part, but missing key dimensions.
- `CONTRADICTED`: Primary source directly refutes the claim.
- `INSUFFICIENT`: Available search results lack requisite detail.
- `OUTDATED`: Claim was previously true but superseded by newer developments.
- `UNVERIFIABLE`: Beyond the reach of open search/public filings.

### Temporal Precision & Provenance
- `event_at`: UTC timestamp of the real-world event.
- `published_at`: UTC timestamp when reporting media published the story.
- `discovered_at`: UTC timestamp when ChangeRadar retrieved the document.
- `is_syndicated`: Boolean flag for syndicated duplicates (e.g. PR Newswire clones).
- `independent_origin_count`: Conservative estimate of editorial origins (distinguishing 10 syndicated articles from 10 independent confirmations).

### Review Baseline & Personal Delta
- Baseline is measured against the user's **last actively reviewed state** (`last_reviewed_at`), not automated background runs.
- `DeltaRecord`:
  - `new_events`: Array of event IDs not present in baseline.
  - `updated_events`: Array of known event IDs with material description/status shifts.
  - `new_evidence_for_claims`: Array of claim IDs with newly discovered corroborations.
  - `changed_assessments`: Array of claim IDs whose status altered.
  - `no_material_change`: Boolean flag.
  - `comparison_incomplete`: Boolean flag for partial search runs.

### Coverage & Search Limitations
- Search results always include a `CoverageReport`:
  - `planned_searches`, `executed_searches`, `failed_searches`.
  - `origin_diversity_score` (unique independent origins / total origins).
  - `gaps`: Explicitly identified unanswered research angles.
  - `warnings`: Syndication notices and crawler limits.

---

## 3. Platform REST API Boundaries (Krishank)

Base Path: `/api/v1`

| Method | Endpoint | Purpose | Request / Response Contract |
|---|---|---|---|
| `GET` | `/sessions` | List sessions | Query: `?scope=PERSONAL\|WORKSPACE`<br>Response: `ResearchSession[]` |
| `POST` | `/sessions` | Create session | Body: `CreateSessionPayload`<br>Response: `ResearchSession` |
| `GET` | `/sessions/:id` | Session details | Response: `ResearchSession` |
| `DELETE` | `/sessions/:id` | Delete session | Response: `204 No Content` |
| `GET` | `/sessions/:id/briefing` | Fetch synthesized briefing | Response: `IntelligenceResult` |
| `POST` | `/sessions/:id/review` | Mark briefing as reviewed | Response: `{ success: true, reviewed_at: ISOString }` |
| `POST` | `/sessions/:id/stress-tests` | Submit talking points | Body: `{ talking_points: string[] }`<br>Response: `StressTestResult` |
| `GET` | `/runs/:job_id` | Poll worker job status | Response: `ResearchJob` |
| `GET` | `/metrics/dashboard` | Dashboard metrics | Response: `DashboardMetrics` |

---

## 4. Mock & Offline Adapter Strategy
To facilitate thorough UI/UX evaluation before live backend deployment, `src/services/mockData.ts` and `src/services/researchService.ts` provide contract-matched fixtures:
- `sess-001` (Acme Corp): Full briefing with syndicated press releases grouped into 1 origin, 14% vs 20% contradicted revenue claims, and stress test suggestions.
- `sess-002` (Dr. Elena Rostova): Person-type dossier with academic and career credentials.
- `sess-003` (BioSynthetix Therapeutics): Workspace-scoped session with partial job status simulation.
- Toggle between live API and mock fixtures at any time using the sidebar data source control or `.env` configuration (`VITE_USE_MOCK_DATA=true`).

