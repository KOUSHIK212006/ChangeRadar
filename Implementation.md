# ChangeRadar — Three-Member Implementation Plan

**Version:** 1.0   
**Project type:** Evidence-first, change-aware meeting intelligence platform

---

## 1. Product overview

### Product vision

**ChangeRadar — Know what changed. Understand what matters. Decide what to do.**

ChangeRadar helps people prepare for important meetings by turning new information about a company, person, market, or topic into a traceable, change-aware briefing.

It is not simply a web-search summarizer. Its central value is helping a user understand:

1. What has changed since they last reviewed the topic?
2. Which developments are genuinely new, and which update an existing development?
3. Which claims are supported, contradicted, incomplete, stale, or not verifiable?
4. How many genuinely independent origins support a claim?
5. What important information may be missing from the research?
6. Are the user's planned talking points still accurate and defensible?

### Core principles

- **Evidence before fluency:** Every material claim in a briefing should be traceable to evidence or explicitly marked as uncertain.
- **Change relative to review state:** A delta is measured against the user's last reviewed state, not merely the previous automated run.
- **Source count is not independence:** Ten articles repeating one press release do not constitute ten independent confirmations.
- **Time is explicit:** Event date, publication date, and discovery time are distinct fields.
- **Uncertainty is visible:** A lack of search results is not proof that nothing happened. Coverage limitations must be shown.
- **Privacy is enforced by the backend:** A client-side route or hidden UI element is never an authorization boundary.
- **One shared intelligence model:** Personal and Workspace research use the same research and evidence concepts, with different ownership and access rules.

## 2. MVP scope and boundaries

### Build first: Personal Research workflow

1. A user creates a research session by entering a target and meeting context.
2. The backend creates a research run and a durable job.
3. The research engine searches, normalizes, and evaluates information.
4. The system extracts and clusters events, claims, sources, and evidence.
5. The user receives a structured briefing with source traceability.
6. The user inspects an event timeline and evidence ledger.
7. The user compares current research with the last reviewed state.
8. The user submits talking points for an evidence-based stress test.
9. The user marks a briefing or its items as reviewed so future deltas have a meaningful baseline.

### Build after the core flow works

- Workspace creation and membership.
- Sharing research sessions with a workspace.
- Workspace-level comments and tasks.
- Invitations, role management, and notifications.

Workspace research must reuse the same `ResearchSession` and intelligence pipeline. Do not introduce a second research engine or duplicate session model.

### Explicitly defer

- Google Calendar synchronization or automatic meeting ingestion.
- Meeting transcription or recording analysis.
- Full CRM integrations.
- A separately deployed intelligence microservice.
- Complex Redis/Celery infrastructure before job volume requires it.
- An opaque pitch-readiness score.
- A separate “Incognito” mode; use clear ownership labels such as **Personal** and **Workspace**.
- A broad team-alignment radar unless it is grounded in explicit, inspectable assumptions and evidence.

Manual research-session creation is sufficient for the MVP. Authentication may be implemented early if required for ownership and privacy testing, but calendar integration must not block the core workflow.

## 3. Team responsibilities

### Frontend and UX

**Technology:** React, TypeScript, Vite, Tailwind CSS, React Router, TanStack Query.

Responsibilities:

- Set up the frontend structure, routing, design system, and responsive application shell.
- Build the dashboard and Personal Research creation flow.
- Build research progress and job-status views.
- Build the results experience: briefing overview, event timeline, evidence ledger, Personal Delta, and Talking-Point Stress Test.
- Display evidence status, source provenance, dates, uncertainty, and coverage limitations clearly.
- Implement empty, loading, partial, retry, and error states.
- Integrate with the backend using the agreed API contract.
- Use mocked responses only when they follow the agreed contract.
- Prepare workspace screens behind a feature flag or as later-stage UI; do not let them delay Personal Research.
- Add frontend tests for critical user flows and state transitions.

**Deliverables:** Responsive React application, research creation-to-results workflow, evidence/change visualizations, typed API integration, frontend tests, and setup documentation.

### AI Research and Intelligence Engine

**Technology:** Python, Tavily search API, provider-agnostic LLM adapter, Pydantic, NLP and evaluation tooling.

The engine initially lives as a Python package inside the backend repository. It is a logical module, not a separately deployed microservice.

Responsibilities:

- Resolve and normalize the research target and context.
- Plan searches based on target, time window, and research objective.
- Integrate with Tavily through a replaceable search adapter.
- Normalize search results and extract source metadata.
- Identify canonical URLs and likely common source origins.
- Resolve entities and aliases.
- Extract candidate events and atomic claims.
- Cluster reports describing the same event.
- Preserve event, publication, and discovery timestamps separately.
- Link claims to supporting, contradicting, and contextual evidence.
- Assess evidence using explicit, inspectable statuses.
- Estimate source-origin independence without treating URL count as independence.
- Identify potentially stale claims using claim-specific volatility and time context.
- Compare current findings with the supplied review baseline.
- Parse talking points into atomic claims and evaluate them against available evidence.
- Produce a coverage report showing searches attempted, sources found, source diversity, failures, and known gaps.
- Return typed, validated output to the backend. The engine must not write directly to application database tables.

**Deliverables:** Modular intelligence package, search and LLM adapters, typed schemas, deterministic unit/integration tests, evaluation dataset and baseline metrics, and documentation of limitations.

### Backend and Platform Architecture

**Technology:** Python, FastAPI, PostgreSQL, SQLAlchemy, Alembic, Pydantic, Docker.

Responsibilities:

- Establish backend structure and configuration.
- Define and maintain the database schema and migrations.
- Implement authentication and user identity.
- Implement Personal and Workspace ownership and access checks.
- Create and manage research sessions, runs, and jobs.
- Implement durable job processing.
- Invoke the intelligence engine through the agreed typed contract.
- Validate engine output and persist it transactionally.
- Expose versioned REST endpoints.
- Implement progress, retry, cancellation, and failure handling.
- Enforce access control on every read and write operation.
- Add backend/integration tests, API documentation, and Docker-based local development instructions.

**Deliverables:** FastAPI application and OpenAPI specification, PostgreSQL schema and migrations, authentication/authorization, worker and orchestration, persistence and API endpoints, tests, Docker setup, and documentation.

### Ownership boundary

The backend owns application persistence and database transactions. The intelligence engine owns research and analysis logic. The frontend owns presentation and user interaction.

The AI workstream must not independently create or modify SQLAlchemy models, open database sessions, or write application records. The backend must not duplicate intelligence logic in API route handlers.

## 4. Git branches and collaboration

Use `main` as the stable integration branch and keep work in focused feature branches.

### Development branches

```text
feature/frontend-app
feature/intelligence-engine
feature/backend-platform
```

### Git workflow

1. Keep `main` buildable and stable.
2. Create the three feature branches from the agreed baseline.
3. Make small, logical commits.
4. Open pull requests into `main`; do not push unfinished work directly to `main`.
5. Require teammate review for shared contracts, database schema, and API behavior.
6. Merge foundational contracts and integration scaffolding early.
7. Rebase or merge updates from `main` regularly.
8. Avoid duplicating schemas or business logic across branches.
9. Use feature flags or contract-matched mocks when UI is ready before its endpoint.
10. Keep `.env` files and API keys out of Git. Commit `.env.example` with safe placeholders.

### Commit conventions

- `feat:` new functionality
- `fix:` bug fix
- `test:` tests
- `refactor:` internal restructuring
- `docs:` documentation
- `chore:` tooling and maintenance

Examples:

```text
feat: add research session creation flow
feat: implement event clustering pipeline
feat: add durable research job processing
test: cover personal session access rules
docs: document intelligence result contract
```

Do not wait until all three workstreams are “finished” before integrating. Establish a thin end-to-end vertical slice early, then improve it incrementally.

## 5. System architecture

### High-level architecture

```text
React + TypeScript Frontend
          | HTTPS / JSON
          v
FastAPI Application
          +---- Authentication and Authorization
          +---- Research Session and Run Services
          +---- Job API / Status API
          +---- PostgreSQL
          |       +---- Users and Workspaces
          |       +---- Sessions, Runs, and Jobs
          |       +---- Sources, Events, Claims, Evidence
          |       +---- Briefings and Review State
          v
Durable Worker Process
          v
Intelligence Engine Package
          +---- Context Resolver
          +---- Research Planner
          +---- Search Provider Adapter (Tavily)
          +---- Source Normalization and Origin Grouping
          +---- Entity Resolution
          +---- Event and Claim Extraction
          +---- Event Clustering
          +---- Evidence Assessment
          +---- Temporal and Volatility Analysis
          +---- Delta Computation
          +---- Talking-Point Stress Test
          +---- Coverage Auditor
          v
Typed Intelligence Result
          v
Backend Validation and Persistence
```

### Runtime recommendation

For the MVP, use one repository and one backend codebase, with the API and worker running as separate processes. They share application services, schemas, and configuration. A practical deployment has a frontend, FastAPI API process, worker process, and PostgreSQL database. Do not introduce independently deployed microservices unless scaling or operational needs justify them.

### Research execution flow

1. User submits a research request.
2. API authenticates the user and validates access to the requested ownership scope.
3. Backend creates or selects a `ResearchSession`.
4. Backend creates a `ResearchRun` and durable `ResearchJob`.
5. Worker claims the job and marks it `RUNNING`.
6. Worker calls the intelligence engine with validated input and the relevant review baseline.
7. Engine searches, normalizes, extracts, clusters, and evaluates evidence.
8. Engine returns a typed `IntelligenceResult` and coverage information.
9. Backend validates the result and persists it in a transaction or well-defined persistence stages.
10. Job/run are marked `COMPLETED`, `PARTIAL`, or an appropriate failure state.
11. Frontend reads progress and fetches the persisted briefing and related records.

### Job processing

Research can take longer than a normal HTTP request. Do not rely on FastAPI `BackgroundTasks` as the durable execution system for long-running research.

For the MVP, use a simple PostgreSQL-backed job queue with safe claiming/locking (for example, row locking with `SKIP LOCKED`) and explicit retry behavior. Keep it small and observable. Consider Redis/Celery or another dedicated queue only when measured workload justifies it.

Suggested job states:

```text
QUEUED
RUNNING
RETRY_WAIT
COMPLETED
PARTIAL
FAILED
CANCELLED
```

A worker crash must not leave a job permanently marked `RUNNING`. Store attempt count, lease/heartbeat or claim time, last error, and next retry time.

## 6. Shared contracts and integration boundaries

This is a prerequisite for parallel development.

### Contract-first agreement

Agree on request/response field names, required and optional fields, identifier format, enum values, timestamp and timezone policy, error shape, partial-result semantics, evidence/source relationships, pagination, API versioning, and compatibility expectations.

Create a shared `contracts/` package or equivalent. Avoid circular imports. The intelligence package must not import SQLAlchemy models.

### Core contract types

```text
ResearchRequest
ResearchContext
ResearchPlan
ResearchBaseline
SourceRecord
SourceOriginRecord
ExtractedEvent
EventVersionRecord
ExtractedClaim
EvidenceRecord
EvidenceAssessment
CoverageReport
IntelligenceResult
JobStatusResponse
ApiError
```

The precise fields must be agreed in the repository. Do not let each member invent a separate representation of the same object.

### Contract responsibilities

- The engine accepts validated research input and returns typed intelligence output.
- The backend validates the output, assigns/maps persistent identifiers, and owns persistence.
- The frontend consumes the backend API contract, not internal engine objects.
- The backend OpenAPI document is the source of truth for frontend API types where practical. Generate TypeScript types from it instead of maintaining duplicate hand-written interfaces.

### Minimum `IntelligenceResult` content

Include run metadata and completion/partial status; search plan and execution summary; sources and origin groupings; events and event versions; atomic claims; evidence links and assessments; coverage report and known limitations; warnings and recoverable errors; and non-secret provider/model metadata needed for reproducibility.

An LLM's self-reported confidence is not proof that a claim is true. Store evidence, provenance, assessment rationale, and uncertainty separately.

## 7. Intelligence model and status definitions

### Event lifecycle

Use lifecycle status only for event progression:

```text
NEW
DEVELOPING
UPDATED
COMPLETED
```

Keep orthogonal conditions separate, for example `DISPUTED` and `UNCERTAIN`. An event can be `DEVELOPING` and `DISPUTED` at the same time. Do not force unrelated dimensions into one status enum.

### Claim/evidence assessment

```text
SUPPORTED
PARTIALLY_SUPPORTED
CONTRADICTED
INSUFFICIENT
OUTDATED
UNVERIFIABLE
```

These statuses describe the relationship between a claim and currently available evidence. They are not a universal truth score.

### Temporal fields

Preserve distinct timestamps where known:

- `event_at`: when the described event happened.
- `published_at`: when the source was published.
- `discovered_at`: when the system found or retrieved it.
- `updated_at`: when the stored record was last updated.

Use timezone-aware UTC timestamps for storage and transmit ISO 8601 timestamps. Preserve original date precision when exact time is unavailable.

### Source independence

Represent source origin separately from individual source pages. Several publishers republishing one press release may be one origin; an official filing and an independent investigative report may be separate origins. A source may support one claim while being irrelevant to another.

Show both the number of source documents and estimated independent origins. Origin classification must be explainable and may be marked uncertain.

### Claim volatility and staleness

Staleness must be claim-specific. A share price, executive role, product availability, and historical acquisition date have different expected rates of change. A newer publication does not automatically make an older claim outdated. Mark a claim `OUTDATED` only when evidence and temporal context justify it.

### Delta semantics

A delta is computed against the user's last reviewed baseline for the relevant session or briefing. Distinguish:

- New event.
- Meaningful update to a known event.
- Newly discovered evidence for an existing claim.
- Changed evidence assessment.
- No material change detected.
- Incomplete comparison because the latest run or baseline is incomplete.

Store review state explicitly. Do not infer that a user reviewed a result merely because it was opened or fetched by the frontend.

### Coverage reporting

Record planned searches, executed searches, search failures/provider limitations, time window covered, source types and origin diversity, important entities/topics not adequately covered, and whether evidence is sufficient for the requested briefing.

A “no new developments found” message must include the scope and limitations of the search supporting it.

## 8. Suggested logical data model

The backend owns the relational schema. This is a logical starting point; not every table is required in the first migration.

### Identity and ownership

| Entity | Purpose |
|---|---|
| `User` | Authenticated application user |
| `Workspace` | Shared team or organization space |
| `WorkspaceMembership` | User membership and role |
| `WorkspaceInvitation` | Optional invitation lifecycle |

### Research lifecycle

| Entity | Purpose |
|---|---|
| `ResearchSession` | Research target, context, and ownership scope |
| `ResearchRun` | One execution of research for a session |
| `ResearchJob` | Durable worker execution and retry state |
| `Briefing` | User-facing synthesized output for a run |
| `ReviewedItem` | Explicit record of what a user reviewed and when |

### Evidence and intelligence

| Entity | Purpose |
|---|---|
| `Source` | Individual retrieved source/document |
| `SourceOrigin` | Canonical publisher, primary origin, or origin cluster |
| `Event` | Normalized real-world development |
| `EventVersion` | Time-stamped changes to an event's known description/status |
| `EventSource` | Many-to-many link between events and sources |
| `Claim` | Atomic factual proposition |
| `Evidence` | Evidence item or excerpt relevant to a claim |
| `ClaimEvidence` | Link between claim and evidence, including stance and rationale |
| `CoverageReport` | Search coverage, limitations, and missing areas |

### User interaction and collaboration

| Entity | Purpose |
|---|---|
| `StressTest` | A submitted set of talking points |
| `StressTestResult` | Assessment and suggested revision for an individual point |
| `ResearchNote` | User-authored note with explicit ownership |
| `WorkspaceTask` | Optional workspace follow-up task |
| `WorkspaceComment` | Optional workspace discussion |
| `AuditEvent` | Optional security-sensitive or important activity record |

### Ownership constraint

Use one `ResearchSession` table for Personal and Workspace research. A session has exactly one ownership scope:

- Personal: `owner_user_id` is set and `workspace_id` is null.
- Workspace: `workspace_id` is set and `owner_user_id` is null.

Enforce this with a database check constraint and application validation. Workspace membership does not grant access to a user's Personal sessions. A workspace administrator must not gain access to Personal research through their workspace role.

If the product later needs a user-owned session shared with selected people, design that as an explicit sharing/ACL model rather than weakening the ownership rule implicitly.

### Relationship guidance

- A session has many runs.
- A run has one job lifecycle record or a clearly defined job-attempt model.
- A run can produce a briefing, sources, events, claims, and a coverage report.
- Events and sources are many-to-many.
- Claims and evidence are many-to-many through `ClaimEvidence`.
- Review state is scoped to the user and relevant session/item.
- Use foreign keys, unique constraints, indexes, and deletion policies deliberately. Avoid storing relationships as unvalidated JSON arrays.

## 9. API design

Use the versioned base path `/api/v1`. Use consistent resource naming and HTTP semantics. Authorize every resource by ownership scope, not by trusting a route prefix or client-supplied ID.

### Authentication and identity

```text
POST   /auth/google
POST   /auth/logout
GET    /users/me
```

Document the OAuth flow, token handling, cookie strategy, CSRF protections, and deployment callback URLs. Never store provider secrets in frontend code.

### Research sessions

```text
POST   /sessions
GET    /sessions
GET    /sessions/{session_id}
PATCH  /sessions/{session_id}
DELETE /sessions/{session_id}
POST   /sessions/{session_id}/runs
GET    /sessions/{session_id}/runs
GET    /sessions/{session_id}/briefing
GET    /sessions/{session_id}/delta
POST   /sessions/{session_id}/review
POST   /sessions/{session_id}/stress-tests
GET    /sessions/{session_id}/stress-tests/{stress_test_id}
POST   /sessions/{session_id}/notes
GET    /sessions/{session_id}/notes
```

Create/list endpoints must support an explicit ownership scope. A session is created as Personal or under a Workspace the user is authorized to use.

### Runs and intelligence records

```text
GET    /runs/{run_id}
GET    /runs/{run_id}/sources
GET    /runs/{run_id}/events
GET    /runs/{run_id}/coverage
GET    /events/{event_id}
GET    /events/{event_id}/versions
GET    /claims/{claim_id}
GET    /claims/{claim_id}/evidence
POST   /runs/{run_id}/cancel
POST   /runs/{run_id}/retry
```

### Workspaces — later milestone

```text
POST   /workspaces
GET    /workspaces
GET    /workspaces/{workspace_id}
PATCH  /workspaces/{workspace_id}
GET    /workspaces/{workspace_id}/members
POST   /workspaces/{workspace_id}/invitations
GET    /workspaces/{workspace_id}/research
POST   /workspaces/{workspace_id}/research
POST   /workspaces/{workspace_id}/tasks
GET    /workspaces/{workspace_id}/tasks
POST   /workspaces/{workspace_id}/comments
GET    /workspaces/{workspace_id}/comments
```

### API behavior requirements

- Return consistent errors with a stable error code and human-readable message.
- Use `401` for unauthenticated requests and `403` or carefully scoped `404` for unauthorized resources, per the information-disclosure policy.
- Validate request bodies and query parameters.
- Paginate potentially large collections.
- Make run creation idempotent where practical, or accept an idempotency key to prevent duplicate jobs on client retries.
- Return job status separately from the final briefing payload.
- Document partial results and retryable failures.
- Never expose API keys, internal stack traces, or private notes in API responses.

## 10. Frontend experience requirements

### Main navigation

Keep the first version focused: Dashboard, Personal Research, Workspace (hidden/disabled or clearly marked as coming later until implemented), and Settings.

### Research creation

Capture only context that materially improves research:

- Target name or topic.
- Target type, if known.
- Meeting purpose or objective.
- Relevant date/time or research time window.
- Optional questions or areas to investigate.
- Optional talking points to stress-test.

Avoid a long form. Allow optional context to be added later.

### Results experience

**Briefing overview:** Key developments, why each matters to the meeting objective, caveats, unresolved questions, and coverage summary.

**Event timeline:** Event date and publication date shown separately; lifecycle and uncertainty/dispute indicators; supporting sources; grouping of updates to the same event.

**Evidence ledger:** Atomic claim, assessment status, supporting and contradicting evidence, source documents and estimated independent origins, assessment rationale, and limitations.

**Personal delta:** What is new since the last reviewed baseline, what changed in known events or claims, what evidence changed, and what could not be compared reliably.

**Talking-point stress test:** Original talking point, extracted factual claims, evidence assessment, explanation and source links, suggested safer wording, and a clear indication when evidence is insufficient to recommend a revision.

### UI states

Every main view must handle initial loading, empty state, in-progress research, partial result, completed result, recoverable error/retry, permanent failure, cancelled run, and stale cached result while a new run is processing.

Do not show a completed state merely because the request to create a run returned successfully.

## 11. Milestone plan

Milestones are integration checkpoints, not isolated hand-offs. Each ends with a demonstrable, tested increment.

### Milestone 0 — Product and contract lock

**Goal:** Agree on the minimum product, data contracts, and integration boundaries before parallel implementation expands.

Frontend and UX:
- Agree on the core user journey and wireframes.
- Define page states and navigation.
- Create the frontend API client boundary and mock strategy.

AI engine:
- Define engine input/output schemas.
- Define initial event, claim, evidence, source, and coverage representations.
- Select initial search and LLM provider adapters.

Backend:
- Create repository structure and development configuration.
- Draft the ERD and ownership rules.
- Define API conventions, error shape, and job lifecycle.

**Acceptance criteria:** MVP scope and deferred features are agreed; shared contracts are committed and reviewed; a sample request/result fixture exists; session ownership and authorization rules are documented; all members can run their module locally.

### Milestone 1 — Foundation and first vertical slice

**Goal:** A user can create a research session and see a real job move through its lifecycle.

Frontend and UX:
- Build application shell and dashboard.
- Build Personal Research creation form.
- Display queued/running/completed/failed job states using the agreed contract.
- Use contract-matched mock data until the API is available.

AI engine:
- Implement package structure and provider interfaces.
- Implement a basic search adapter and source normalization.
- Return a minimal typed result from deterministic fixtures and a real search run.

Backend:
- Implement FastAPI application and database connection.
- Add initial migrations and core identity/session/run/job models.
- Implement session and run creation.
- Implement durable job claiming and status endpoints.

**Acceptance criteria:** A valid request creates a persisted session, run, and job; the worker claims the job and updates status; the frontend displays backend status; a deterministic fixture passes through the full API-worker-engine boundary.

### Milestone 2 — Core research and evidence pipeline

**Goal:** Produce a structured briefing from retrieved sources.

Frontend and UX:
- Build briefing overview.
- Build source list and source detail/provenance view.
- Build event timeline and initial event cards.
- Handle partial and failed research states.

AI engine:
- Implement source normalization and canonical URL handling.
- Implement entity resolution.
- Extract candidate events and atomic claims.
- Cluster duplicate reports describing the same event.
- Link claims to evidence and return assessment rationale.
- Add source-origin grouping with conservative independence estimates.

Backend:
- Persist sources, origins, events, event versions, claims, evidence, and relationships.
- Implement result and briefing endpoints.
- Validate engine output and make persistence retry-safe.

**Acceptance criteria:** A run produces a persisted briefing; each material claim is traceable to evidence and sources; reports about one development can be grouped without losing citations; UI distinguishes source-document count from estimated independent-origin count; partial search failure is visible.

### Milestone 3 — Temporal intelligence, coverage, and Personal Delta

**Goal:** Explain what changed since the user's last review.

Frontend and UX:
- Build detailed event timeline.
- Build evidence ledger and assessment filters.
- Build Personal Delta view.
- Add explicit “Mark reviewed” interaction and baseline date.

AI engine:
- Implement temporal normalization and event-version comparison.
- Implement claim-specific volatility/staleness assessment.
- Implement evidence updates and changed-assessment detection.
- Implement coverage reporting.
- Compute candidate deltas against a supplied review baseline.

Backend:
- Persist event versions and coverage reports.
- Implement reviewed-item or review-snapshot persistence.
- Implement delta endpoint and baseline selection.
- Ensure review state is scoped to the correct user and session.

**Acceptance criteria:** A user can mark a briefing/items as reviewed; later runs compare against that baseline; UI distinguishes new events from updates; newly discovered articles are not automatically called new events; coverage limitations accompany “no material change” results.

### Milestone 4 — Talking-point stress test

**Goal:** Let a user test planned statements against the evidence ledger.

Frontend and UX:
- Build talking-point input and submission flow.
- Display extracted claims and evidence assessments.
- Show supporting and contradicting evidence.
- Display suggested revisions with source links and uncertainty.

AI engine:
- Split talking points into atomic factual claims.
- Match claims to existing evidence and identify when more research is needed.
- Assign explicit assessment statuses.
- Generate grounded explanations and safer wording suggestions.
- Avoid inventing evidence or treating opinions as factual errors.

Backend:
- Persist stress tests and individual results.
- Implement create/read endpoints.
- Associate results with the relevant session and evidence context.
- Enforce ownership and access checks.

**Acceptance criteria:** Each point produces inspectable claim assessments; evidence-backed assessments link to stored evidence; unsupported/unverifiable points are not presented as confirmed falsehoods; suggested wording introduces no facts absent from evidence; results survive refresh.

### Milestone 5 — Security, reliability, and release hardening

**Goal:** Make the Personal Research MVP safe, predictable, and demonstrable.

Frontend and UX:
- Complete responsive behavior and accessibility basics.
- Verify loading, empty, partial, failure, retry, and cancellation states.
- Remove or gate unfinished workspace controls.

AI engine:
- Add deterministic regression fixtures.
- Measure extraction, clustering, evidence assessment, and delta quality.
- Add timeouts, provider error handling, and structured warnings.
- Document limitations and model/provider configuration.

Backend:
- Complete authorization tests and database constraints.
- Add job retry, stale-job recovery, and cancellation behavior.
- Add logging and run-level correlation IDs.
- Add suitable database backup/deployment configuration for the demo environment.
- Verify secrets and sensitive data are not logged or exposed.

**Acceptance criteria:** Critical end-to-end tests pass; worker restart does not permanently strand a job; unauthorized-access tests pass; provider failure produces an understandable partial/failed result; clean setup is documented.

### Milestone 6 — Workspace collaboration (post-MVP)

**Goal:** Share selected research through an explicit workspace boundary.

Frontend and UX:
- Add workspace switcher and dashboard.
- Add member, shared research, comment, and task screens.
- Clearly distinguish Personal from Workspace content.

AI engine:
- Reuse the existing engine.
- Add workspace-specific context only where it changes the research request.
- Do not fork the event, claim, or evidence pipeline.

Backend:
- Add workspace and membership endpoints.
- Add invitations and roles if required.
- Enforce membership checks on every workspace resource.
- Keep Personal resources inaccessible through workspace APIs.

**Acceptance criteria:** Members access only permitted workspace sessions; workspace membership never grants access to Personal sessions; removing a member revokes subsequent access; workspace notes/comments cannot leak into Personal research or another workspace.

## 12. Testing and evaluation strategy

### Frontend tests

- Research form validation.
- Job progress and status transitions.
- Rendering source, event, claim, and evidence records.
- Delta display and reviewed-state interaction.
- Stress-test result rendering.
- Empty, partial, retry, and failure states.
- Access-denied behavior.

### Backend tests

- Session creation and ownership constraints.
- User and workspace authorization.
- Job claiming, retry, cancellation, and stale-job recovery.
- Engine contract validation.
- Persistence relationships and transaction behavior.
- Pagination and filtering.
- API error shape and idempotency behavior.

### Intelligence engine tests

Use deterministic fixtures so core logic can be tested without live search or LLM calls. Include:

- Multiple articles describing one event.
- Syndicated copies of one press release.
- Independent sources reporting the same development.
- Conflicting claims from credible sources.
- An old claim that remains historically true.
- A volatile claim that may have become stale.
- Event date differing from publication date.
- Search failure or empty search result.
- A later run with no material change.
- A later run with a genuinely new event.
- Talking points with supporting, contradicting, and insufficient evidence.

### Evaluation metrics

| Area | Suggested metric |
|---|---|
| Event extraction | Precision and recall on a labelled sample |
| Event clustering | Pairwise precision/recall or cluster quality |
| Source deduplication | Duplicate rate and missed-duplicate rate |
| Origin independence | Accuracy on manually labelled origin groups |
| Claim extraction | Atomicity and factual extraction accuracy |
| Evidence assessment | Agreement with human-reviewed labels |
| Temporal analysis | Event-date and update classification accuracy |
| Delta | Precision and recall of meaningful changes |
| Stress test | Supported/contradicted/insufficient classification quality |
| Coverage | Planned-versus-executed search completeness |
| Operations | Run duration, failure rate, retry rate, and cost per run |

Record the evaluation dataset and method. Do not claim high accuracy without a defined test set.

## 13. Security and privacy requirements

These are release-blocking requirements:

1. A user must not read another user's Personal session, run, briefing, notes, or stress test.
2. A workspace member must not read resources from a workspace they do not belong to.
3. Workspace administrators must not access a member's Personal research through workspace privileges.
4. Knowing or guessing a session, run, event, or claim ID must not bypass authorization.
5. Removing a workspace member must revoke access to subsequent requests.
6. Private notes must never be returned by workspace endpoints.
7. Every endpoint reading or mutating a resource must perform server-side authorization.
8. API keys and OAuth secrets must be stored in environment variables or a secret manager, never in source control or frontend bundles.
9. Logs must not contain access tokens, API keys, or unnecessary private research content.
10. Validate user-provided content and treat retrieved web content as untrusted data.
11. Instructions found in retrieved pages must never override system behavior or application policy.
12. Apply sensible request limits, provider timeouts, and rate limits.

Automate negative tests for: User A accessing User B's Personal session; a non-member accessing a Workspace session; a Workspace administrator accessing a member's Personal session; a removed member accessing a former Workspace session; changing a resource ID to another user's resource; and a Workspace endpoint attempting to return private notes.

## 14. Demo acceptance scenario

Prepare one repeatable demo dataset and use it across all workstreams.

### First run

- User creates a Personal Research session for a company and records the purpose of an upcoming partnership meeting.
- Engine retrieves several reports about one major company development.
- Duplicate/syndicated reports are clustered.
- Briefing shows one event with multiple source documents and a conservative independent-origin estimate.
- Claims link to supporting or contradicting evidence.
- User reviews the briefing and marks it as reviewed.

### Second run

- Engine retrieves an update to the existing event and one genuinely new development.
- Delta identifies the update and new development relative to the reviewed baseline.
- It does not label every newly retrieved article as a new event.
- Coverage report identifies important gaps or failed searches.

### Talking-point test

- User submits one supported point, one outdated or contradicted point, and one point with insufficient evidence.
- System explains each result and offers a grounded revision where appropriate.
- Every evidence-backed explanation links to the underlying source.

Automate this scenario as an integration test where practical and use it for the final demonstration.

## 15. Definition of done

A feature is not complete merely because its main screen or function exists. It is done when:

- Its contract and behavior are documented.
- Input validation and expected error behavior are implemented.
- Relevant unit and integration tests pass.
- Authorization is enforced where data is involved.
- Loading, empty, partial, and failure states are handled where applicable.
- Logs and errors are useful without exposing secrets or private data.
- It is integrated with `main` and does not break the build.
- Setup or usage documentation is updated.
- It can be demonstrated from a clean, documented environment.

### MVP release gate

The Personal Research MVP is ready for demonstration only when a user can:

1. Create a Personal research session.
2. Start a run and see durable job progress.
3. Receive a structured briefing from the intelligence engine.
4. Inspect events, claims, sources, and evidence.
5. Understand source origins and coverage limitations.
6. Mark the briefing as reviewed.
7. Run research again and see a meaningful delta against that review state.
8. Submit talking points and inspect evidence-backed stress-test results.
9. Refresh the application and retrieve persisted results.
10. Pass critical privacy and authorization tests.

## 16. Coordination checklist

### Before parallel development

- [ ] Agree on MVP scope and defer calendar integration and advanced collaboration.
- [ ] Commit shared request/result contracts.
- [ ] Agree on event, claim, evidence, job, and ownership status definitions.
- [ ] Agree on timestamp and timezone handling.
- [ ] Agree on database ownership model and initial ERD.
- [ ] Agree on API paths, error shape, and OpenAPI generation.
- [ ] Create a deterministic sample request and result fixture.
- [ ] Confirm local setup for frontend, API, worker, and database.

### During implementation

- [ ] Integrate a thin vertical slice early.
- [ ] Keep frontend mocks aligned with the actual contract.
- [ ] Keep database writes inside backend services.
- [ ] Keep intelligence logic out of route handlers.
- [ ] Add tests with each feature.
- [ ] Merge small pull requests regularly.
- [ ] Re-run end-to-end tests after contract or schema changes.
- [ ] Track known limitations rather than hiding them.

### Before the demo

- [ ] Run the complete demo scenario from a clean environment.
- [ ] Verify the second-run delta uses the reviewed baseline.
- [ ] Verify source-origin grouping on syndicated content.
- [ ] Verify partial failures and no-result cases.
- [ ] Run all authorization tests.
- [ ] Confirm no secrets are committed or exposed.
- [ ] Confirm README covers installation, environment variables, migrations, API startup, worker startup, and frontend startup.

## 17. Final implementation priority

The greatest project risk is building three polished but disconnected modules. Avoid that by prioritizing integration over breadth.

Build in this order:

1. Shared contracts and ownership model.
2. Session → run → durable job → worker → typed engine result.
3. Persisted sources, events, claims, evidence, and briefing.
4. Frontend evidence-first results experience.
5. Explicit review state and delta computation.
6. Talking-point stress test.
7. Security and reliability hardening.
8. Workspace collaboration after the Personal workflow is stable.

**The MVP succeeds when ChangeRadar can reliably explain what changed, show the evidence behind that explanation, and distinguish what it knows from what it cannot yet verify.**

---

## 18. Detailed task allocation — three members

This section is the execution-level ownership map. The role descriptions and milestone responsibilities above explain the workstreams; this section makes the individual tasks, hand-offs, and shared responsibilities explicit.

### 18.1 Ownership at a glance

| Member | Workstream | Primary ownership | Git branch |
|---|---|---|---|
| **Koushik** | Frontend and UX | React application, user flows, visualizations, frontend API integration | `feature/frontend-app` |
| **Surjith** | AI Research and Intelligence Engine | Search, extraction, event/claim intelligence, evidence assessment, delta and stress-test logic | `feature/intelligence-engine` |
| **Krishank** | Backend and Platform | FastAPI, database, authentication/authorization, jobs, persistence, API contracts and deployment | `feature/backend-platform` |

**Ownership does not mean working in isolation.** Each member is accountable for their workstream, but shared contracts, integration, review, and end-to-end testing are team responsibilities.

### 18.2 Member 1 — Koushik: Frontend and UX

**Owns:** `feature/frontend-app`

#### Tasks

**A. Frontend foundation**
- Create and configure the React + TypeScript + Vite project.
- Configure Tailwind CSS, React Router, TanStack Query, linting, formatting, and environment variables.
- Establish a scalable folder structure, for example:
  - `app/` — app setup, providers, and routing
  - `components/` — reusable UI components
  - `features/research/` — research creation and results
  - `features/briefing/` — briefing and event views
  - `features/evidence/` — claims and evidence ledger
  - `features/delta/` — reviewed state and delta
  - `features/stress-test/` — talking-point analysis
  - `lib/api/` — API client and generated types
  - `types/` — frontend-only view types, not duplicate API contracts
- Build the application shell, navigation, responsive layout, and reusable design primitives.

**B. Personal Research workflow**
- Build the dashboard and research-session list.
- Build the create-research form with target, target type, meeting objective, time window, research questions, and optional talking points.
- Connect form submission to the session/run creation API.
- Show queued, running, partial, completed, failed, and cancelled states.
- Implement progress polling or the agreed live-update mechanism.

**C. Briefing and evidence experience**
- Build the briefing overview and key-development cards.
- Build the event timeline with event date and publication date clearly separated.
- Build source detail/provenance presentation.
- Build the evidence ledger with claim status, evidence links, source-document count, and independent-origin estimate.
- Show uncertainty, conflicting evidence, and coverage limitations without hiding them.

**D. Change and stress-test experience**
- Build the explicit “Mark reviewed” interaction.
- Build the Personal Delta view using the backend's baseline and delta response.
- Build the talking-point input, result list, claim assessments, evidence links, and suggested wording.
- Make it clear when a point is unsupported or unverifiable rather than displaying it as definitively false.

**E. Quality and delivery**
- Implement loading, empty, partial, retry, error, and stale-result states.
- Add responsive and accessibility checks.
- Add component and user-flow tests.
- Keep API calls in a dedicated client/query layer; do not call endpoints ad hoc from every component.
- Use mock fixtures that match the agreed API contract until backend endpoints are ready.
- Prepare workspace screens only after the Personal Research workflow is integrated; keep them gated until backend authorization is implemented.

#### Koushik's deliverables
- Running frontend application.
- Research creation-to-results user journey.
- Briefing, event timeline, evidence ledger, Personal Delta, and stress-test screens.
- Typed API client and generated API types where practical.
- Frontend tests and frontend setup documentation.

#### Koushik depends on
- **From Krishank:** OpenAPI endpoints, authentication/session behavior, job status shape, pagination, and error schema.
- **From Surjith (through the backend contract):** agreed meaning of event, claim, evidence, origin count, assessment statuses, coverage, and delta fields.

#### Koushik must provide to the team
- Wireframes or screen flows early, not only at the end.
- Required response fields for each screen, documented as API feedback rather than independently invented fields.
- A working frontend against deterministic fixtures before live integration.
- A list of missing API capabilities discovered during implementation.

---

### 18.3 Member 2 — Surjith: AI Research and Intelligence Engine

**Owns:** `feature/intelligence-engine`

#### Tasks

**A. Engine foundation**
- Create the Python intelligence package inside the agreed backend repository structure.
- Define clear module boundaries and typed Pydantic input/output models.
- Implement provider interfaces for search and LLM calls so providers can be replaced.
- Add configuration, timeout, retry, and structured logging behavior for external calls.
- Keep the engine independent of FastAPI route handlers and SQLAlchemy models.

**B. Research and source pipeline**
- Implement research-context resolution.
- Implement research planning for target, meeting objective, time window, and questions.
- Implement the Tavily adapter.
- Normalize URLs, titles, publishers, snippets, and publication timestamps.
- Identify canonical URLs and likely syndicated/republished content.
- Group documents by likely source origin and preserve uncertainty in origin classification.

**C. Entity, event, and claim pipeline**
- Resolve target entities and aliases.
- Extract candidate events from retrieved documents.
- Extract atomic factual claims rather than broad paragraphs.
- Cluster documents that describe the same real-world event.
- Preserve event date, publication date, and discovery time independently.
- Create event versions when later evidence materially changes the known description or status.

**D. Evidence intelligence**
- Link each claim to relevant supporting, contradicting, or contextual evidence.
- Implement the agreed assessment statuses:
  - `SUPPORTED`
  - `PARTIALLY_SUPPORTED`
  - `CONTRADICTED`
  - `INSUFFICIENT`
  - `OUTDATED`
  - `UNVERIFIABLE`
- Produce a concise assessment rationale and traceable evidence references.
- Estimate source-origin independence conservatively; do not equate article count with independent confirmation.
- Implement claim-specific volatility/staleness logic.
- Keep LLM confidence separate from evidence strength and assessment status.

**E. Delta, coverage, and talking-point analysis**
- Accept the review baseline as an explicit engine input.
- Identify new events, event updates, newly discovered evidence, and changed assessments.
- Report when a comparison is incomplete because a run or baseline is incomplete.
- Implement coverage reporting: planned searches, executed searches, failures, time window, source diversity, and gaps.
- Parse talking points into atomic factual claims.
- Match those claims to existing evidence and flag when additional research is required.
- Generate suggested wording only when it can be grounded in evidence.

**F. Evaluation and delivery**
- Create deterministic fixtures for duplicate, syndicated, independent, conflicting, stale, and no-result cases.
- Add unit and integration tests for each pipeline stage.
- Build a small manually labelled evaluation set.
- Track extraction, clustering, origin grouping, evidence assessment, temporal, delta, and stress-test quality.
- Document limitations, provider configuration, and expected engine behavior.

#### Surjith's deliverables
- Modular Python intelligence package.
- Tavily and LLM provider adapters.
- Pydantic engine contracts.
- Structured intelligence result with sources, origins, events, claims, evidence, coverage, and warnings.
- Deterministic test fixtures and evaluation report.
- Engine setup and module documentation.

#### Surjith depends on
- **From Krishank:** agreed contract package, worker invocation interface, configuration conventions, and persistence feedback.
- **From Koushik:** user-facing research inputs and the information the UI needs to display; this should be agreed before changing schemas.

#### Surjith must provide to the team
- A minimal deterministic engine result early, before the full intelligence pipeline is complete.
- Example input and output fixtures.
- Stable enum definitions and field semantics.
- A clear list of fields that are uncertain, optional, or unavailable from the source.
- No direct database writes; return structured results to the backend.

---

### 18.4 Member 3 — Krishank: Backend and Platform Architecture

**Owns:** `feature/backend-platform`

#### Tasks

**A. Backend foundation**
- Create the FastAPI project structure and configuration.
- Configure PostgreSQL, SQLAlchemy, Alembic, and Pydantic settings.
- Establish local development and Docker configuration.
- Create the shared contract location and coordinate the initial contract review with both members.
- Publish and maintain the OpenAPI specification.

**B. Database and identity**
- Design and implement the initial ERD and migrations.
- Implement `User`, `ResearchSession`, `ResearchRun`, and `ResearchJob`.
- Implement the single `ResearchSession` ownership model for Personal and Workspace scopes.
- Enforce the ownership constraint with database and application validation.
- Implement authentication and user identity.
- Implement authorization checks as reusable backend services/dependencies.
- Add Workspace and membership tables only when the workspace milestone begins.

**C. API and application services**
- Implement session creation, listing, retrieval, and update endpoints.
- Implement run creation and run-status endpoints.
- Implement briefing, sources, events, claims, evidence, coverage, delta, review, notes, and stress-test endpoints as each milestone reaches integration.
- Standardize pagination, error responses, validation, and idempotency behavior.
- Keep route handlers thin; put business orchestration in application/service modules.

**D. Durable job processing**
- Implement a PostgreSQL-backed job queue for the MVP.
- Implement safe job claiming/locking, attempt count, retry schedule, and stale-job recovery.
- Run the worker as a separate process using shared backend code.
- Invoke Surjith's engine through the agreed typed contract.
- Handle success, partial result, failure, retry, and cancellation.
- Add run/job correlation IDs and useful operational logs.

**E. Persistence and integration**
- Validate the engine's returned `IntelligenceResult`.
- Map engine output to database records.
- Persist sources, source origins, events, event versions, claims, evidence, relationships, and coverage.
- Make persistence safe against duplicate processing and worker retries.
- Persist briefing output and reviewed-item state.
- Implement delta retrieval against the user's explicit review baseline.
- Persist talking-point stress tests and their results.

**F. Security, testing, and delivery**
- Enforce authorization for every resource read and write.
- Add tests for Personal isolation and Workspace membership.
- Add API/worker/database integration tests.
- Ensure secrets are loaded from environment variables or a secret manager.
- Add Docker instructions, migrations, health checks, and clean setup documentation.
- Prepare deployment configuration suitable for the MVP.

#### Krishank's deliverables
- FastAPI backend and OpenAPI documentation.
- PostgreSQL schema and Alembic migrations.
- Authentication and authorization.
- Session/run/job lifecycle and worker.
- Engine integration and persistence layer.
- REST endpoints for the MVP.
- Backend tests, Docker setup, and backend documentation.

#### Krishank depends on
- **From Surjith:** stable engine input/output models and deterministic sample results.
- **From Koushik:** screen/API needs and agreed user flows, so endpoints support real UI requirements.
- **From both:** decisions on enums, timestamps, ownership scope, and error/partial-result semantics.

#### Krishank must provide to the team
- A working API skeleton and OpenAPI document early.
- Database migrations and a repeatable local setup.
- A stable worker-to-engine invocation interface.
- API examples and error responses.
- A seeded development account and deterministic demo data where appropriate.

---

### 18.5 Shared responsibilities and decision ownership

Some work must not be assigned to one person alone because it affects all three modules.

| Shared area | Driver | Required contributors | Expected output |
|---|---|---|---|
| Product scope and MVP priorities | All three | All three | Agreed scope and deferred-feature list |
| Engine request/result contract | Surjith | Krishank, Koushik | Versioned Pydantic schemas and fixtures |
| Database schema and ownership rules | Krishank | Surjith, Koushik | ERD, migrations, ownership constraints |
| API and frontend contract | Krishank | Koushik, Surjith | OpenAPI specification and example responses |
| UX flow and display requirements | Koushik | Krishank, Surjith | Wireframes and required-field checklist |
| Event/claim/evidence semantics | Surjith | Krishank, Koushik | Status definitions and examples |
| End-to-end integration | Krishank coordinates | All three | Working vertical slice and integration tests |
| Demo scenario and acceptance | All three | All three | Repeatable demo dataset and checklist |
| Release sign-off | All three | All three | Passing tests, security checks, and demo |

The driver coordinates and prepares the proposal; decisions that change shared contracts or user-visible semantics require agreement from all affected members.

---

### 18.6 Milestone-by-milestone ownership matrix

`A` = accountable owner for delivery; `C` = contributes/reviews; `—` = not a primary task in that milestone.

| Milestone | Koushik — Frontend | Surjith — Intelligence | Krishank — Backend |
|---|---|---|---|
| **M0: Contract lock** | A: user journey, wireframes, UI states | A: engine schemas and intelligence semantics | A: ERD, API conventions, ownership and job model |
| **M1: First vertical slice** | A: app shell, research form, job status UI | A: provider interface, basic search, minimal typed result | A: session/run/job API, DB, worker and status |
| **M2: Core research** | A: briefing, source and event views | A: source normalization, entity/event/claim extraction, clustering | A: persistence and result APIs |
| **M3: Delta and coverage** | A: evidence ledger, mark-reviewed flow, delta UI | A: temporal analysis, evidence updates, coverage and delta logic | A: review-state persistence, event versions and delta API |
| **M4: Stress test** | A: talking-point input and result UI | A: atomic claim parsing, evidence matching and grounded suggestions | A: stress-test persistence and endpoints |
| **M5: Hardening** | A: responsive/accessibility and UI failure states | A: regression fixtures and quality evaluation | A: authorization, job recovery, deployment and integration tests |
| **M6: Workspace (post-MVP)** | A: workspace screens | C: reuse engine and support workspace context | A: workspace schema, roles, membership and authorization |

This matrix clarifies delivery ownership; it does not remove the shared review and integration duties described above.

---

### 18.7 Recommended weekly execution rhythm

1. **Planning:** Agree on the week's end-to-end outcome and acceptance criteria.
2. **Contract check:** Identify whether any API, schema, enum, or field meaning is changing.
3. **Parallel implementation:** Each member works on their owned branch against the agreed contract.
4. **Mid-week integration:** Merge small completed slices and resolve mismatches while they are still small.
5. **End-to-end verification:** Run at least one user journey through frontend, API, worker, engine, and database.
6. **Review:** Record completed work, known gaps, blockers, and the next integration target.

Do not measure progress only by the number of screens, endpoints, or AI modules completed. Measure it by working user journeys that cross all three workstreams.

---

### 18.8 First tasks to start with

To avoid three members waiting on one another, begin with these parallel tasks after agreeing on the shared contract:

| Koushik | Surjith | Krishank |
|---|---|---|
| Create frontend app shell and research form using the sample request fixture. | Create engine package and return a deterministic sample `IntelligenceResult`. | Create FastAPI app, database connection, and session/run/job skeleton. |
| Build job-status UI against the agreed response fixture. | Implement Tavily adapter behind a provider interface. | Implement job creation/status endpoints and a basic worker. |
| Prepare briefing and evidence wireframes. | Define source/event/claim/evidence structures and test fixtures. | Publish OpenAPI and connect the worker to the engine contract. |

**First integration checkpoint:** Submit one research request from the frontend, create a session/run/job in the backend, execute the engine (initially with a deterministic fixture if needed), persist the returned result, and display the job completion in the frontend. Only after this works should the team expand the pipeline and UI in parallel.

