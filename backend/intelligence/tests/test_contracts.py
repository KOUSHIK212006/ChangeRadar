"""Tests for contracts.py — validates that fixtures deserialise correctly into Pydantic models."""

import json
from pathlib import Path
import pytest

from intelligence.contracts import (
    ResearchRequest,
    IntelligenceResult,
    EvidenceAssessment,
    EventLifecycle,
    ClaimVolatility,
    EvidenceStance,
    EngineResultStatus,
)

FIXTURES = Path(__file__).parent.parent / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


class TestResearchRequest:
    def test_loads_from_fixture(self):
        data = load_fixture("sample_request.json")
        req = ResearchRequest.model_validate(data)
        assert req.session_id == "sess-001"
        assert req.job_id == "job-001"
        assert req.context.target_name == "Acme Corp"
        assert req.context.time_window_days == 30
        assert len(req.context.research_questions) == 4
        assert len(req.context.talking_points) == 2
        assert req.baseline is None

    def test_context_requires_target_name(self):
        data = load_fixture("sample_request.json")
        data["context"].pop("target_name")
        with pytest.raises(Exception):
            ResearchRequest.model_validate(data)

    def test_context_requires_meeting_objective(self):
        data = load_fixture("sample_request.json")
        data["context"].pop("meeting_objective")
        with pytest.raises(Exception):
            ResearchRequest.model_validate(data)

    def test_time_window_bounds(self):
        data = load_fixture("sample_request.json")
        data["context"]["time_window_days"] = 0
        with pytest.raises(Exception):
            ResearchRequest.model_validate(data)

        data["context"]["time_window_days"] = 366
        with pytest.raises(Exception):
            ResearchRequest.model_validate(data)


class TestIntelligenceResult:
    def test_loads_from_fixture(self):
        data = load_fixture("sample_result.json")
        result = IntelligenceResult.model_validate(data)
        assert result.session_id == "sess-001"
        assert result.job_id == "job-001"
        assert result.status == EngineResultStatus.COMPLETED

    def test_sources(self):
        data = load_fixture("sample_result.json")
        result = IntelligenceResult.model_validate(data)
        assert len(result.sources) == 4
        syndicated = [s for s in result.sources if s.is_syndicated]
        assert len(syndicated) == 1
        assert syndicated[0].syndication_confidence > 0.8

    def test_origins(self):
        data = load_fixture("sample_result.json")
        result = IntelligenceResult.model_validate(data)
        assert len(result.origins) == 3
        independent = [o for o in result.origins if o.is_independent]
        assert len(independent) == 2

    def test_events(self):
        data = load_fixture("sample_result.json")
        result = IntelligenceResult.model_validate(data)
        assert len(result.events) == 3
        statuses = {e.lifecycle_status for e in result.events}
        assert EventLifecycle.NEW in statuses
        assert EventLifecycle.DEVELOPING in statuses

    def test_claims_have_valid_assessments(self):
        valid = {
            EvidenceAssessment.SUPPORTED,
            EvidenceAssessment.PARTIALLY_SUPPORTED,
            EvidenceAssessment.CONTRADICTED,
            EvidenceAssessment.INSUFFICIENT,
            EvidenceAssessment.OUTDATED,
            EvidenceAssessment.UNVERIFIABLE,
        }
        data = load_fixture("sample_result.json")
        result = IntelligenceResult.model_validate(data)
        for claim in result.claims:
            assert claim.assessment in valid

    def test_claims_have_valid_volatility(self):
        valid = {ClaimVolatility.LOW, ClaimVolatility.MEDIUM, ClaimVolatility.HIGH}
        data = load_fixture("sample_result.json")
        result = IntelligenceResult.model_validate(data)
        for claim in result.claims:
            assert claim.volatility in valid

    def test_evidence_has_valid_stance(self):
        valid = {EvidenceStance.SUPPORTING, EvidenceStance.CONTRADICTING, EvidenceStance.CONTEXTUAL}
        data = load_fixture("sample_result.json")
        result = IntelligenceResult.model_validate(data)
        for claim in result.claims:
            for ev in claim.evidence:
                assert ev.relevance in valid

    def test_llm_confidence_is_separate_from_assessment(self):
        """LLM confidence must be stored but must not equal the assessment string."""
        data = load_fixture("sample_result.json")
        result = IntelligenceResult.model_validate(data)
        for claim in result.claims:
            assert isinstance(claim.llm_confidence, float)
            assert 0.0 <= claim.llm_confidence <= 1.0
            assert isinstance(claim.assessment, str)

    def test_independent_origin_count_lte_source_doc_count(self):
        """Independent origins can never exceed source document count."""
        data = load_fixture("sample_result.json")
        result = IntelligenceResult.model_validate(data)
        for claim in result.claims:
            assert claim.independent_origin_count <= claim.source_doc_count

    def test_coverage_report_present(self):
        data = load_fixture("sample_result.json")
        result = IntelligenceResult.model_validate(data)
        assert result.coverage.planned_searches >= result.coverage.executed_searches
        assert result.coverage.executed_searches >= result.coverage.failed_searches
        assert 0.0 <= result.coverage.origin_diversity_score <= 1.0

    def test_delta_is_none_on_first_run(self):
        data = load_fixture("sample_result.json")
        result = IntelligenceResult.model_validate(data)
        assert result.delta is None

    def test_stress_test_present(self):
        data = load_fixture("sample_result.json")
        result = IntelligenceResult.model_validate(data)
        assert result.stress_test is not None
        assert len(result.stress_test.points) == 2

    def test_contradicted_talking_point(self):
        data = load_fixture("sample_result.json")
        result = IntelligenceResult.model_validate(data)
        revenue_point = result.stress_test.points[1]
        assert revenue_point.assessments[0].assessment == EvidenceAssessment.CONTRADICTED
        assert revenue_point.suggested_wording is not None

    def test_provider_metadata_present(self):
        data = load_fixture("sample_result.json")
        result = IntelligenceResult.model_validate(data)
        assert "search_provider" in result.provider_metadata
        assert "llm_model" in result.provider_metadata
        assert "run_at" in result.provider_metadata
