"""Intelligence pipeline stages.

Modules:
- planner: generates search queries and entity aliases from research context
- normalizer: deduplicates sources, detects syndication, groups origins
- extractor: extracts events and atomic claims from sources
- clusterer: merges duplicate events describing the same development
- assessor: assesses claims against evidence, applies staleness logic
- coverage: builds coverage report and detects topic gaps
- delta: computes change summary against the user's last reviewed baseline
- stress_test: assesses talking points against the evidence ledger
"""
