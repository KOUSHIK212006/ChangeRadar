# ChangeRadar Cross-Functional Integration & System Architecture Document

This document records the cross-functional contracts, architecture, and verification results connecting:
- **Koushik** (Frontend Architecture, UI/UX Design & Client Layer)
- **Krishank** (Backend Platform, Database Schema, Migrations & REST Endpoints)
- **Surjith** (AI Research, Intelligence Contracts, Provenance & Verification Engine)

---

## 1. Ownership & Boundary Constraints
- Every `ResearchSession` is strictly bounded by ownership scope:
  - `PERSONAL`: `owner_user_id` set, `workspace_id` is null. Strictly private to the individual user.
  - `WORKSPACE`: `workspace_id` set, `owner_user_id` is null. Shared within workspace boundaries.
- The UI strictly enforces this separation through separate scope selection (`Personal` vs `Workspace`) and view filtering.
- Client-side navigation separates Personal investigations from Workspace dossiers; Krishank's FastAPI backend enforces authorization on all read and write endpoints.

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

## 3. Platform REST API Endpoints (Krishank & Koushik)

Base Path: `/api/v1`

| Method | Endpoint | Purpose | Request / Response Contract |
|---|---|---|---|
| `GET` | `/sessions` | List sessions | Query: `?scope=PERSONAL\|WORKSPACE`<br>Response: `List[ResearchSessionResponse]` |
| `POST` | `/sessions` | Create session | Body: `CreateSessionRequest`<br>Response: `ResearchSessionResponse` (201 Created) |
| `GET` | `/sessions/{id}` | Session details | Response: `ResearchSessionResponse` |
| `DELETE` | `/sessions/{id}` | Delete session | Response: `204 No Content` |
| `GET` | `/sessions/{id}/briefing` | Fetch synthesized briefing | Response: `IntelligenceResult` |
| `GET` | `/sessions/{id}/delta` | Fetch Personal Delta | Response: `DeltaRecord` |
| `POST` | `/sessions/{id}/review` | Mark briefing as reviewed | Response: `MarkReviewedResponse` |
| `POST` | `/sessions/{id}/stress-tests` | Submit talking points | Body: `StressTestSubmissionRequest`<br>Response: `StressTestResult` |
| `GET` | `/runs/{job_id}` | Poll worker job status | Response: `ResearchJobResponse` |
| `GET` | `/metrics/dashboard` | Dashboard metrics | Response: `DashboardMetricsResponse` |

---

## 4. End-to-End Test & Verification Summary

### Frontend Verification (`ChangeRadar/frontend`)
- **Unit & Component Tests:** `vitest run`
  - 5 test suites, **19 passing tests** (100% pass rate).
  - Tests covering `ClaimTable`, `TalkingPointTester`, `ResearchForm`, `Badge`, and `researchService`.
- **Production Build:** `npm run build`
  - TypeScript strict type-checking passed with 0 errors.
  - Vite production bundle generated cleanly (`dist/` 1.05 kB HTML, 29.16 kB CSS, 772.55 kB JS).

### Backend & Intelligence Verification (`ChangeRadar/backend`)
- **Intelligence Contracts:** `python -m pytest intelligence/tests/test_contracts.py`
  - **18 passing tests** (100% pass rate) verifying Pydantic models, JSON schema serialization, source origin grouping, and evaluation fixtures.
- **Database Schema & ORM:** `python -m pytest tests/test_database_schema.py`
  - **6 passing tests** (100% pass rate) validating SQLAlchemy 2.0 declarative models, check constraints, indexes, and relationships.
- **REST API & Service Handlers:** `python -m pytest tests/test_sessions_api.py`
  - **7 passing tests** (100% pass rate) validating session listing, scope filtering, investigation initialization, synthesized briefing contracts, review baseline establishment, talking point contradiction detection, and session deletion.
- **Total Automated Tests:** **50 passing tests across the entire monorepo**.
