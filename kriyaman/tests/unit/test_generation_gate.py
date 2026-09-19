import pytest
from domain.errors import PolicyViolationError
from domain.models import (
    ContextPackage,
    EvidenceAssessment,
    EvidenceItem,
    ExecutionBudgets,
    UsageSnapshot,
)
from application.controller import AgentController
from application.evidence_judge import EvidenceJudge
from application.graph.nodes import GraphNodes
from application.graph.state import GraphState
from application.retrieval_agent import RetrievalAgent


def _make_state(**kwargs) -> GraphState:
    base: GraphState = {
        "run_id": "run_gate_test",
        "session_id": "sess_1",
        "user_query": "test query",
        "normalized_query": "test query",
        "status": "running",
        "controller_plan": None,
        "plan_history": [],
        "evidence": [],
        "evidence_assessment": None,
        "memory_items": [],
        "tool_results": [],
        "retrieval_iterations": 1,
        "tool_calls": 0,
        "budgets": ExecutionBudgets(),
        "usage": UsageSnapshot(),
        "execution_events": [],
        "context_package": None,
        "answer": None,
        "failure": None,
    }
    base.update(kwargs)  # type: ignore
    return base


def test_generation_gate_rejects_missing_assessment():
    nodes = GraphNodes(
        controller=AgentController(),
        retrieval_agent=RetrievalAgent(),
        evidence_judge=EvidenceJudge(),
    )
    state = _make_state(evidence_assessment=None, context_package=ContextPackage(system_instructions="", normalized_query=""))

    with pytest.raises(PolicyViolationError) as exc:
        nodes.generate_answer_node(state)
    assert "Attempted generation with invalid assessment decision 'None'" in str(exc.value)


def test_generation_gate_rejects_abstention():
    nodes = GraphNodes(
        controller=AgentController(),
        retrieval_agent=RetrievalAgent(),
        evidence_judge=EvidenceJudge(),
    )
    assessment = EvidenceAssessment(
        decision="abstain", coverage_score=0.0, quality_score=0.0, confidence=1.0, reason_code="abstain"
    )
    state = _make_state(evidence_assessment=assessment, context_package=ContextPackage(system_instructions="", normalized_query=""))

    with pytest.raises(PolicyViolationError) as exc:
        nodes.generate_answer_node(state)
    assert "Attempted generation with invalid assessment decision 'abstain'" in str(exc.value)


def test_generation_gate_rejects_missing_context_package():
    nodes = GraphNodes(
        controller=AgentController(),
        retrieval_agent=RetrievalAgent(),
        evidence_judge=EvidenceJudge(),
    )
    assessment = EvidenceAssessment(
        decision="sufficient", coverage_score=1.0, quality_score=1.0, confidence=1.0, reason_code="ok"
    )
    state = _make_state(evidence_assessment=assessment, context_package=None)

    with pytest.raises(PolicyViolationError) as exc:
        nodes.generate_answer_node(state)
    assert "ContextPackage must be built before generate_answer" in str(exc.value)


def test_generation_gate_allows_sufficient():
    from application.answer_service import AnswerService
    from tests.fakes.fake_llm import FakeLLMProvider

    fake_llm = FakeLLMProvider(
        structured_response={
            "answer_text": "Verified text from document.",
            "citation_ids": ["ev_1"],
            "confidence": 0.95,
            "needs_follow_up": False,
        }
    )
    nodes = GraphNodes(
        controller=AgentController(),
        retrieval_agent=RetrievalAgent(),
        evidence_judge=EvidenceJudge(),
        answer_service=AnswerService(llm_provider=fake_llm),
    )
    assessment = EvidenceAssessment(
        decision="sufficient", coverage_score=0.9, quality_score=0.9, confidence=0.9, reason_code="ok"
    )
    ctx = ContextPackage(
        system_instructions="sys",
        normalized_query="query",
        evidence_items=[
            EvidenceItem(
                evidence_id="ev_1",
                source_type="document",
                source_id="d1",
                content="Verified text",
                retrieval_method="vector",
            )
        ],
    )
    state = _make_state(evidence_assessment=assessment, context_package=ctx)

    result = nodes.generate_answer_node(state)
    assert result["status"] == "answer"
    assert result["answer"] is not None
    assert "ev_1" in result["answer"].citation_ids


def test_generation_gate_no_llm_abstains():
    nodes = GraphNodes(
        controller=AgentController(),
        retrieval_agent=RetrievalAgent(),
        evidence_judge=EvidenceJudge(),
        answer_service=None,
    )
    assessment = EvidenceAssessment(
        decision="sufficient", coverage_score=0.9, quality_score=0.9, confidence=0.9, reason_code="ok"
    )
    ctx = ContextPackage(
        system_instructions="sys",
        normalized_query="query",
        evidence_items=[],
    )
    state = _make_state(evidence_assessment=assessment, context_package=ctx)

    result = nodes.generate_answer_node(state)
    assert result["status"] == "abstention"
    assert result["answer"].confidence == 0.0
    assert "No generation LLM provider is configured" in result["answer"].answer_text


