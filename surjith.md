# Surjith — Intelligence Engine Implementation Plan

**Branch:** `feature/intelligence-engine`  
**Package location:** `backend/intelligence/`  
**Rule:** No SQLAlchemy imports. No DB writes. Return typed Pydantic output only.

---

## Package Structure (create this first)

```
backend/
  intelligence/
    __init__.py
    contracts.py
    engine.py
    config.py
    providers/
      __init__.py
      base.py
      tavily.py
      llm.py
    pipeline/
      __init__.py
      planner.py
      normalizer.py
      extractor.py
      clusterer.py
      assessor.py
      delta.py
      stress_test.py
      coverage.py
    fixtures/
      sample_request.json
      sample_result.json
    tests/
      __init__.py
      test_contracts.py
      test_normalizer.py
      test_extractor.py
      test_clusterer.py
      test_assessor.py
      test_delta.py
      test_stress_test.py
      test_coverage.py
```

---

## Step 1 — `contracts.py` (do this first, unblocks everyone)

Define all Pydantic input/output models. These are the shared contracts Krishank and Koushik depend on.

### Input contracts

```python
class ResearchContext(BaseModel):
    target_name: str
    target_type: Optional[str]
    meeting_objective: str
    time_window_days: int = 30
    research_questions: list[str] = []
    talking_points: list[str] = []

class ResearchBaseline(BaseModel):
    baseline_result_id: str
    reviewed_at: datetime
    known_event_ids: list[str]
    known_claim_ids: list[str]

class ResearchRequest(BaseModel):
    session_id: str
    job_id: str
    context: ResearchContext
    baseline: Optional[ResearchBaseline] = None
```

### Output contracts

```python
class SourceRecord(BaseModel):
    source_id: str                  # stable hash of canonical URL
    url: str
    canonical_url: str
    title: str
    publisher: str
    snippet: str
    published_at: Optional[datetime]
    discovered_at: datetime
    is_syndicated: bool = False
    syndication_confidence: float = 0.0

class SourceOriginRecord(BaseModel):
    origin_id: str
    label: str                      # e.g. "Reuters", "Company Press Release"
    source_ids: list[str]
    is_independent: bool
    independence_confidence: float  # 0.0–1.0, be conservative

class ExtractedEvent(BaseModel):
    event_id: str
    title: str
    description: str
    lifecycle_status: str           # NEW | DEVELOPING | UPDATED | COMPLETED
    is_disputed: bool = False
    is_uncertain: bool = False
    event_at: Optional[datetime]    # when the event happened
    published_at: Optional[datetime]
    discovered_at: datetime
    source_ids: list[str]
    origin_ids: list[str]
    claim_ids: list[str]

class EvidenceRecord(BaseModel):
    evidence_id: str
    excerpt: str
    source_id: str
    relevance: str                  # SUPPORTING | CONTRADICTING | CONTEXTUAL

class ExtractedClaim(BaseModel):
    claim_id: str
    text: str                       # atomic factual statement
    assessment: str                 # EvidenceVerificationStatus values
    assessment_rationale: str
    evidence: list[EvidenceRecord]
    source_doc_count: int
    independent_origin_count: int   # conservative estimate
    volatility: str                 # LOW | MEDIUM | HIGH
    is_stale: bool = False
    llm_confidence: float           # kept separate from assessment

class EventVersionRecord(BaseModel):
    version_id: str
    event_id: str
    description: str
    changed_at: datetime
    change_summary: str

class DeltaRecord(BaseModel):
    new_events: list[str]           # event_ids
    updated_events: list[str]
    new_evidence_for_claims: list[str]   # claim_ids
    changed_assessments: list[str]
    no_material_change: bool
    comparison_incomplete: bool
    incompleteness_reason: Optional[str]

class CoverageReport(BaseModel):
    planned_searches: int
    executed_searches: int
    failed_searches: int
    time_window_days: int
    source_types_found: list[str]
    origin_diversity_score: float   # 0.0–1.0
    gaps: list[str]                 # topics/entities not adequately covered
    warnings: list[str]

class IntelligenceResult(BaseModel):
    session_id: str
    job_id: str
    status: str                     # COMPLETED | PARTIAL | FAILED
    sources: list[SourceRecord]
    origins: list[SourceOriginRecord]
    events: list[ExtractedEvent]
    event_versions: list[EventVersionRecord]
    claims: list[ExtractedClaim]
    coverage: CoverageReport
    delta: Optional[DeltaRecord]
    warnings: list[str]
    provider_metadata: dict         # model name, search provider, run timestamp
```

**Deliver this + fixtures immediately. Krishank cannot wire the worker without it.**

---

## Step 2 — `fixtures/` (deliver alongside contracts)

Create two JSON files that match the contracts exactly.

### `fixtures/sample_request.json`

```json
{
  "session_id": "sess-001",
  "job_id": "job-001",
  "context": {
    "target_name": "Acme Corp",
    "target_type": "company",
    "meeting_objective": "Partnership discussion",
    "time_window_days": 30,
    "research_questions": ["Any recent leadership changes?", "New product launches?"],
    "talking_points": ["Acme is expanding into APAC", "Their Q3 revenue grew 20%"]
  },
  "baseline": null
}
```

### `fixtures/sample_result.json`

Populate with 2 events, 3 claims, 4 sources, 2 origins, a coverage report, and no delta (baseline is null). Use realistic but fictional data. Every field in `IntelligenceResult` must be present.

---

## Step 3 — `config.py`

```python
from pydantic_settings import BaseSettings

class IntelligenceSettings(BaseSettings):
    TAVILY_API_KEY: str = ""
    LLM_PROVIDER: str = "openai"        # openai | anthropic
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.1
    LLM_TIMEOUT_SECONDS: int = 30
    SEARCH_TIMEOUT_SECONDS: int = 15
    SEARCH_MAX_RESULTS: int = 10
    MAX_RETRIES: int = 2

    model_config = {"env_file": ".env", "extra": "ignore"}

intelligence_settings = IntelligenceSettings()
```

---

## Step 4 — `providers/base.py` (abstract interfaces)

```python
from abc import ABC, abstractmethod
from intelligence.contracts import SourceRecord, ResearchContext

class SearchProvider(ABC):
    @abstractmethod
    def search(self, query: str, context: ResearchContext) -> list[SourceRecord]:
        ...

class LLMProvider(ABC):
    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        ...
```

Never call Tavily or OpenAI directly in pipeline modules. Always go through these interfaces.

---

## Step 5 — `providers/tavily.py`

### What it does
- Accepts a query string + `ResearchContext`
- Calls Tavily Search API
- Returns `list[SourceRecord]`

### Tavily API call

```
POST https://api.tavily.com/search
Headers: Content-Type: application/json
Body:
{
  "api_key": "<TAVILY_API_KEY>",
  "query": "<query>",
  "search_depth": "advanced",
  "include_answer": false,
  "include_raw_content": false,
  "max_results": 10,
  "include_domains": [],
  "exclude_domains": []
}

Response fields used:
  results[].url
  results[].title
  results[].content       → snippet
  results[].published_date
  results[].score
```

### Normalization inside the adapter
- Set `discovered_at = datetime.utcnow()`
- Derive `canonical_url` by stripping UTM params and trailing slashes
- Generate `source_id = sha256(canonical_url)[:16]`
- Set `is_syndicated = False`, `syndication_confidence = 0.0` (syndication is detected later in normalizer)
- Wrap in try/except; on failure raise a typed `SearchProviderError`

---

## Step 6 — `providers/llm.py`

### What it does
- Wraps OpenAI (or Anthropic) chat completion
- Returns raw string — JSON parsing happens in the calling pipeline module
- Enforces timeout and retry from config

### OpenAI API call

```
POST https://api.openai.com/v1/chat/completions
Headers:
  Authorization: Bearer <OPENAI_API_KEY>
  Content-Type: application/json
Body:
{
  "model": "gpt-4o-mini",
  "temperature": 0.1,
  "messages": [
    {"role": "system", "content": "<system_prompt>"},
    {"role": "user", "content": "<user_prompt>"}
  ]
}

Response field used:
  choices[0].message.content
```

- Always set `temperature: 0.1` for determinism
- Always ask for JSON output in the system prompt
- Parse with `json.loads()` and validate with Pydantic in the calling module
- On JSON parse failure, log and raise `LLMParseError`

---

## Step 7 — `pipeline/planner.py`

### Input
`ResearchContext`

### Output
```python
class ResearchPlan(BaseModel):
    queries: list[str]          # 3–6 targeted search queries
    entity_aliases: list[str]   # alternate names for the target
    time_filter: str            # e.g. "past month"
```

### How it works
1. Call LLM with the target name, type, objective, and questions
2. Ask it to generate search queries that cover: recent news, leadership, financials, products, controversies
3. Ask it to list known aliases/alternate names for the target entity
4. Parse JSON response into `ResearchPlan`

### System prompt template
```
You are a research planner. Given a target entity and meeting context, 
generate specific search queries and entity aliases.
Return JSON: {"queries": [...], "entity_aliases": [...], "time_filter": "..."}
Do not include generic queries. Focus on what would matter for the meeting objective.
```

---

## Step 8 — `pipeline/normalizer.py`

### Input
`list[SourceRecord]` (raw from Tavily)

### Output
`tuple[list[SourceRecord], list[SourceOriginRecord]]`

### Steps
1. **Canonical URL deduplication** — group sources with same `canonical_url`, keep one, mark others as duplicates
2. **Syndication detection** — call LLM with a batch of titles+snippets, ask which ones appear to be republications of the same original story. Set `is_syndicated=True` and `syndication_confidence` on matches
3. **Origin grouping** — call LLM to cluster sources by likely original publisher/origin. Ask it to be conservative: only group when confident. Set `is_independent` and `independence_confidence`
4. Build `SourceOriginRecord` for each cluster

### LLM prompt for syndication (batch)
```
Given these news articles (title + snippet), identify which appear to be 
republications of the same original story. Return JSON:
{"syndication_groups": [[source_id, source_id], ...]}
Be conservative. Only group when the content is clearly the same story.
```

### LLM prompt for origin grouping
```
Given these sources with their publishers, group them by likely original 
information origin (e.g. one press release republished by many = one origin).
Return JSON: {"origin_groups": [{"label": "...", "source_ids": [...], "is_independent": true/false, "confidence": 0.0-1.0}]}
```

---

## Step 9 — `pipeline/extractor.py`

### Input
`list[SourceRecord]`, `ResearchContext`

### Output
`tuple[list[ExtractedEvent], list[ExtractedClaim]]`

### Steps

**Event extraction:**
1. For each source, call LLM to extract candidate events
2. Each event must have: title, description, event_at (if mentioned), lifecycle_status
3. Preserve `published_at` from the source, set `discovered_at = now()`

**Claim extraction:**
1. For each event, call LLM to extract atomic factual claims
2. Each claim must be a single verifiable statement (not a paragraph)
3. Link each claim to the source_ids it came from

### LLM prompt for event extraction
```
Extract distinct real-world events from this article. 
Each event is a specific development that happened (not an opinion or prediction).
Return JSON: {"events": [{"title": "...", "description": "...", "event_at": "ISO date or null", "lifecycle_status": "NEW|DEVELOPING|UPDATED|COMPLETED", "is_disputed": false, "is_uncertain": false}]}
```

### LLM prompt for claim extraction
```
From this event description, extract atomic factual claims.
Each claim must be a single, specific, verifiable statement.
Do not include opinions, predictions, or vague statements.
Return JSON: {"claims": [{"text": "...", "volatility": "LOW|MEDIUM|HIGH"}]}
```

---

## Step 10 — `pipeline/clusterer.py`

### Input
`list[ExtractedEvent]`, `list[SourceRecord]`

### Output
`list[ExtractedEvent]` (deduplicated, with merged source_ids)

### Steps
1. Call LLM with all event titles+descriptions
2. Ask it to identify which events describe the same real-world development
3. Merge duplicate events: keep the most detailed description, union the source_ids and origin_ids
4. Generate stable `event_id = sha256(canonical_title)[:16]`

### LLM prompt
```
Given these extracted events, identify which ones describe the same real-world development.
Return JSON: {"clusters": [[event_index, event_index, ...], ...]}
Each cluster is a group of events that are the same development.
Singletons are valid clusters.
```

---

## Step 11 — `pipeline/assessor.py`

### Input
`list[ExtractedClaim]`, `list[SourceRecord]`, `list[SourceOriginRecord]`

### Output
`list[ExtractedClaim]` (with assessment, rationale, evidence, origin counts filled in)

### Steps
1. For each claim, find relevant source excerpts (keyword match + LLM relevance check)
2. Call LLM to assess the claim against the evidence
3. Assign one of: `SUPPORTED | PARTIALLY_SUPPORTED | CONTRADICTED | INSUFFICIENT | OUTDATED | UNVERIFIABLE`
4. Count `source_doc_count` and `independent_origin_count` (from origin groupings, not raw source count)
5. Set `is_stale` based on volatility + age of most recent supporting source
6. Store `llm_confidence` separately — never use it as the assessment status

### LLM prompt for assessment
```
Assess this claim against the provided evidence excerpts.
Claim: "<claim text>"
Evidence: [{"excerpt": "...", "source": "...", "published_at": "..."}]

Return JSON:
{
  "assessment": "SUPPORTED|PARTIALLY_SUPPORTED|CONTRADICTED|INSUFFICIENT|OUTDATED|UNVERIFIABLE",
  "rationale": "one sentence explanation",
  "supporting_evidence_ids": [...],
  "contradicting_evidence_ids": [...],
  "confidence": 0.0-1.0
}

Rules:
- SUPPORTED: multiple independent sources confirm it
- PARTIALLY_SUPPORTED: some evidence supports, some is missing
- CONTRADICTED: evidence directly contradicts the claim
- INSUFFICIENT: not enough evidence to assess
- OUTDATED: claim was true but evidence suggests it has changed
- UNVERIFIABLE: cannot be assessed from available sources
```

### Staleness logic
```python
def is_stale(claim, sources) -> bool:
    if claim.volatility == "LOW":
        return False
    if claim.volatility == "HIGH":
        # stale if newest supporting source > 7 days old
        ...
    if claim.volatility == "MEDIUM":
        # stale if newest supporting source > 30 days old
        ...
```

---

## Step 12 — `pipeline/coverage.py`

### Input
`ResearchPlan`, executed query count, failed query count, `list[SourceRecord]`, `list[SourceOriginRecord]`, `ResearchContext`

### Output
`CoverageReport`

### Steps
1. Count planned vs executed vs failed searches
2. Collect unique publisher types from sources
3. Compute `origin_diversity_score = unique_independent_origins / total_origins` (capped at 1.0)
4. Call LLM to identify gaps: topics from `research_questions` not covered by retrieved sources
5. Add warnings for: zero results, all sources from one origin, search failures

### LLM prompt for gap detection
```
Given these research questions and the sources retrieved, identify which questions 
were not adequately addressed.
Research questions: [...]
Sources retrieved (titles + snippets): [...]
Return JSON: {"gaps": ["question or topic not covered", ...]}
```

---

## Step 13 — `pipeline/delta.py`

### Input
`IntelligenceResult` (current), `ResearchBaseline` (from request, may be None)

### Output
`Optional[DeltaRecord]`

### Steps
1. If `baseline is None`, return `None` (no delta on first run)
2. Compare `current.events[].event_id` against `baseline.known_event_ids` → new events
3. For events in both: compare descriptions via LLM → updated events
4. Compare `current.claims[].claim_id` against `baseline.known_claim_ids` → new evidence
5. For claims in both: compare assessment status → changed assessments
6. If current run is `PARTIAL`, set `comparison_incomplete=True`

### LLM prompt for event update detection
```
Has this event description changed materially from the baseline?
Baseline: "<old description>"
Current: "<new description>"
Return JSON: {"is_material_change": true/false, "change_summary": "..."}
```

---

## Step 14 — `pipeline/stress_test.py`

### Input
`list[str]` (talking points), `list[ExtractedClaim]`, `list[SourceRecord]`

### Output
```python
class StressTestPointResult(BaseModel):
    original_point: str
    extracted_claims: list[str]
    assessments: list[ExtractedClaim]
    suggested_wording: Optional[str]    # only if grounded in evidence
    needs_more_research: bool

class StressTestResult(BaseModel):
    points: list[StressTestPointResult]
```

### Steps
1. For each talking point, call LLM to split into atomic claims
2. Match each atomic claim against existing `ExtractedClaim` list (fuzzy text match + LLM confirmation)
3. If no match found, set `needs_more_research=True`
4. For matched claims, use their existing assessment
5. Generate `suggested_wording` only when assessment is `SUPPORTED` or `PARTIALLY_SUPPORTED` and evidence exists
6. Never invent evidence. Never call an unsupported point "false" — use `INSUFFICIENT` or `UNVERIFIABLE`

### LLM prompt for splitting talking points
```
Split this talking point into atomic factual claims (one verifiable fact each).
Talking point: "<text>"
Return JSON: {"claims": ["...", "..."]}
```

### LLM prompt for suggested wording
```
Rewrite this talking point to be more accurate based on the evidence.
Original: "<text>"
Evidence: [{"excerpt": "...", "source": "..."}]
Assessment: PARTIALLY_SUPPORTED
Return JSON: {"suggested_wording": "..."}
Only rewrite if you can ground every fact in the evidence provided.
If you cannot, return {"suggested_wording": null}
```

---

## Step 15 — `engine.py` (main entry point)

This is what Krishank's worker calls. One function, typed input, typed output.

```python
from intelligence.contracts import ResearchRequest, IntelligenceResult

def run_intelligence_engine(request: ResearchRequest) -> IntelligenceResult:
    ...
```

### Full pipeline execution order

```
1.  planner.plan(request.context)
        → ResearchPlan (queries, aliases, time_filter)

2.  For each query in plan.queries:
        tavily_provider.search(query, request.context)
        → list[SourceRecord] (raw)

3.  normalizer.normalize(all_raw_sources)
        → (list[SourceRecord], list[SourceOriginRecord])

4.  extractor.extract_events(sources, request.context)
        → list[ExtractedEvent]

5.  extractor.extract_claims(events, sources)
        → list[ExtractedClaim]

6.  clusterer.cluster_events(events, sources)
        → list[ExtractedEvent] (deduplicated)

7.  assessor.assess_claims(claims, sources, origins)
        → list[ExtractedClaim] (with assessments filled)

8.  coverage.build_report(plan, executed, failed, sources, origins, request.context)
        → CoverageReport

9.  delta.compute(current_result, request.baseline)
        → Optional[DeltaRecord]

10. If request.context.talking_points:
        stress_test.run(talking_points, claims, sources)
        → StressTestResult (stored separately, not in IntelligenceResult)

11. Assemble and return IntelligenceResult
```

### Error handling in engine.py
- Catch `SearchProviderError` → set status `PARTIAL`, add to warnings, continue with empty sources
- Catch `LLMParseError` on any stage → log, skip that item, add warning, continue
- If 0 sources retrieved → set status `PARTIAL`, coverage gaps = ["No sources retrieved"]
- Never raise from `run_intelligence_engine` — always return an `IntelligenceResult` with appropriate status

---

## Step 16 — `engine.py` deterministic fixture mode

Before real API keys are available, support a fixture mode so Krishank can wire the worker immediately.

```python
def run_intelligence_engine(request: ResearchRequest) -> IntelligenceResult:
    if intelligence_settings.USE_FIXTURE_MODE:
        return _load_fixture_result(request.session_id, request.job_id)
    return _run_live_pipeline(request)
```

Add `USE_FIXTURE_MODE: bool = True` to `IntelligenceSettings` (default True until keys are configured).

---

## Step 17 — Add dependencies to `requirements.txt`

Add these to `backend/requirements.txt`:

```
tavily-python>=0.3.0
openai>=1.30.0
```

No other new dependencies needed. Pydantic and httpx are already present.

---

## Step 18 — Tests (one file per pipeline module)

### Priority order for tests

1. `test_contracts.py` — validate sample_result.json loads into `IntelligenceResult` without error
2. `test_normalizer.py` — syndication detection, canonical URL dedup, origin grouping
3. `test_assessor.py` — each of the 6 assessment statuses, staleness logic
4. `test_delta.py` — new event, updated event, no change, incomplete comparison
5. `test_stress_test.py` — supported point, contradicted point, insufficient evidence point
6. `test_extractor.py` — atomic claim extraction, event extraction
7. `test_clusterer.py` — duplicate event merging
8. `test_coverage.py` — gap detection, diversity score

### Test fixture cases to cover (from Implementation.md §12)
- Multiple articles → one event (clusterer)
- Syndicated copies of one press release (normalizer)
- Independent sources for same development (assessor: SUPPORTED)
- Conflicting claims from credible sources (assessor: CONTRADICTED)
- Old claim that remains historically true (assessor: not OUTDATED)
- Volatile claim that may be stale (assessor: OUTDATED)
- Event date differs from publication date (extractor)
- Search failure / empty result (engine error handling)
- Second run with no material change (delta: no_material_change=True)
- Second run with genuinely new event (delta: new_events populated)
- Talking point with supporting evidence (stress_test: SUPPORTED)
- Talking point with contradicting evidence (stress_test: CONTRADICTED)
- Talking point with no evidence (stress_test: INSUFFICIENT, needs_more_research=True)

All tests must run without live API calls. Use `unittest.mock.patch` on provider methods.

---

## Delivery order (what to hand off and when)

| Deliver | To whom | When |
|---|---|---|
| `contracts.py` + `fixtures/` | Krishank + Koushik | Day 1 — unblocks worker wiring and frontend mocks |
| `engine.py` in fixture mode | Krishank | Day 1–2 — worker can call engine immediately |
| `config.py` + `providers/base.py` | Krishank | Day 2 |
| `providers/tavily.py` + `providers/llm.py` | Self | Day 2–3 |
| `pipeline/planner.py` + `pipeline/normalizer.py` | Self | Day 3–4 |
| `pipeline/extractor.py` + `pipeline/clusterer.py` | Self | Day 4–5 |
| `pipeline/assessor.py` | Self | Day 5–6 |
| `pipeline/coverage.py` + `pipeline/delta.py` | Krishank | Day 6–7 |
| `pipeline/stress_test.py` | Krishank | Day 7–8 |
| All tests passing | Team | Day 8–9 |
| Evaluation report + docs | Team | Day 9–10 |

---

## What Surjith must NOT do

- Do not import from `app.models` or `app.core.database`
- Do not open a database session
- Do not write records to any table
- Do not call FastAPI route handlers
- Do not duplicate `EvidenceVerificationStatus` — reuse values from `app/models/enums.py` as string literals in contracts
- Do not treat LLM confidence as the evidence assessment status
- Do not call an unsupported claim "false" — use `INSUFFICIENT` or `UNVERIFIABLE`
- Do not count article count as independent origin count

---

## What Surjith must provide to the team

- `contracts.py` on Day 1 (hard dependency for Krishank and Koushik)
- `fixtures/sample_result.json` on Day 1
- `USE_FIXTURE_MODE=True` engine on Day 2 (Krishank wires worker)
- Stable enum string values — do not rename after Krishank has mapped them to DB
- A `CHANGELOG.md` inside `intelligence/` noting any contract field changes
