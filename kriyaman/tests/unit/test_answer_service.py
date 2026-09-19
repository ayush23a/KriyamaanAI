import pytest
from domain.errors import PolicyViolationError
from domain.models import (
    Answer,
    ContextPackage,
    EvidenceAssessment,
    EvidenceItem,
)
from application.answer_service import AnswerService
from tests.fakes.fake_llm import FakeLLMProvider


def test_answer_service_citation_verification():
    fake_llm = FakeLLMProvider()
    service = AnswerService(llm_provider=fake_llm)

    evidence = [
        EvidenceItem(
            evidence_id="ev_valid_1",
            source_type="document",
            source_id="d1",
            content="Valid content 1",
            retrieval_method="vector",
        ),
        EvidenceItem(
            evidence_id="ev_valid_2",
            source_type="document",
            source_id="d2",
            content="Valid content 2",
            retrieval_method="vector",
        ),
    ]

    # LLM returns an answer with a real ID and a hallucinated ID
    raw_answer = Answer(
        answer_text="Here is the claim.",
        citation_ids=["ev_valid_1", "ev_hallucinated_999"],
        confidence=0.9,
    )

    verified = service.validate_citations(raw_answer, evidence)

    # Hallucinated ID must be filtered out
    assert "ev_valid_1" in verified.citation_ids
    assert "ev_hallucinated_999" not in verified.citation_ids
    assert len(verified.citation_ids) == 1


def test_answer_service_generation_gate_rejects_abstention():
    fake_llm = FakeLLMProvider()
    service = AnswerService(llm_provider=fake_llm)

    pkg = ContextPackage(
        system_instructions="rules",
        normalized_query="query",
        evidence_items=[],
    )

    assessment = EvidenceAssessment(
        decision="abstain",
        coverage_score=0.0,
        quality_score=0.0,
        confidence=1.0,
        reason_code="no_evidence",
    )

    with pytest.raises(PolicyViolationError) as exc:
        service.generate(pkg, assessment)

    assert "Generation gate rejected" in str(exc.value)


def test_answer_service_generation_gate_rejects_clarification():
    fake_llm = FakeLLMProvider()
    service = AnswerService(llm_provider=fake_llm)

    pkg = ContextPackage(
        system_instructions="rules",
        normalized_query="ambiguous",
        evidence_items=[],
    )

    assessment = EvidenceAssessment(
        decision="clarification",
        coverage_score=0.0,
        quality_score=1.0,
        confidence=1.0,
        reason_code="ambiguous",
    )

    with pytest.raises(PolicyViolationError) as exc:
        service.generate(pkg, assessment)

    assert "Generation gate rejected" in str(exc.value)


def test_answer_service_successful_generation():
    fake_llm = FakeLLMProvider(
        structured_response=Answer(
            answer_text="Returns are allowed within 30 days.",
            citation_ids=["ev_1"],
            confidence=0.95,
        )
    )
    service = AnswerService(llm_provider=fake_llm)

    evidence = [
        EvidenceItem(
            evidence_id="ev_1",
            source_type="document",
            source_id="d1",
            content="Returns accepted in 30 days.",
            retrieval_method="vector",
        )
    ]

    pkg = ContextPackage(
        system_instructions="rules",
        normalized_query="return window",
        evidence_items=evidence,
    )

    assessment = EvidenceAssessment(
        decision="sufficient",
        coverage_score=0.9,
        quality_score=0.9,
        confidence=0.95,
        reason_code="sufficient",
    )

    answer = service.generate(pkg, assessment)
    assert answer.answer_text == "Returns are allowed within 30 days."
    assert answer.citation_ids == ["ev_1"]
    assert answer.confidence == 0.95

