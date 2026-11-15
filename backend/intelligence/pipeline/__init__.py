"""Intelligence pipeline stages.

Modules:
- planner: generates search queries and entity aliases from research context (Stage A: 1 LLM call)
- normalizer: deterministic deduplication, syndication detection, origin grouping (Stage B & D: 0 LLM calls)
- extractor: batched unified event and atomic claim extraction (Stage C: 1 LLM call for typical batch)
- clusterer: deterministic event deduplication and merging (Stage D: 0 LLM calls)
- assessor: batched multi-claim evidence assessment (Stage E: 1 LLM call)
- coverage: deterministic coverage statistics and gap detection (0 LLM calls)
- delta: deterministic baseline comparison and temporal change detection (Stage F: 0 LLM calls)
- briefing: synthesized executive briefing generation (Stage G: 1 LLM call)
- stress_test: conditional batched talking point stress testing (Stage H: 1 LLM call if points provided)
"""
