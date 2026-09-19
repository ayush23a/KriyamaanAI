from decimal import Decimal
from datetime import datetime
import pytest
from pydantic import ValidationError
from domain.models import (
    AcquisitionPlan,
    Answer,
    CallBudget,
    ChatMessage,
    ContextPackage,
    EvidenceAssessment,
    EvidenceItem,
    ExecutionBudgets,
    ExecutionEvent,
    MemoryItem,
    MemoryPrincipal,
    ToolContext,
    ToolResult,
    UsageSnapshot,
)


def test_execution_budgets_defaults():
    budgets = ExecutionBudgets()
    assert budgets.max_retrieval_iterations == 3
    assert budgets.max_tool_calls == 3
    assert budgets.max_latency_ms == 30_000
    assert budgets.max_input_tokens == 12_000
    assert budgets.max_output_tokens == 2_000
    assert budgets.max_estimated_cost_usd == Decimal("0.25")


def test_acquisition_plan_valid():
    plan = AcquisitionPlan(
        action="vector_search",
        query="What is the refund policy?",
        top_k=5,
        rerank=True,
        reason_code="initial_query",
        expected_information_gain="high",
    )
    assert plan.action == "vector_search"
    assert plan.top_k == 5
    assert plan.rerank is True


def test_acquisition_plan_no_acquisition():
    plan = AcquisitionPlan(
        action="no_acquisition_required",
        reason_code="conversational_greeting",
        expected_information_gain="low",
    )
    assert plan.action == "no_acquisition_required"
    assert plan.query is None


def test_evidence_item_provenance():
    item = EvidenceItem(
        evidence_id="ev_001",
        source_type="document",
        source_id="doc_123",
        title="Terms of Service",
        content="All refunds processed within 30 days.",
        document_id="doc_123",
        chunk_id="chk_456",
        retrieval_method="vector_similarity",
        retrieval_score=0.92,
    )
    assert item.evidence_id == "ev_001"
    assert item.source_type == "document"
    assert item.document_id == "doc_123"
    assert item.chunk_id == "chk_456"
    assert item.retrieval_score == 0.92


def test_evidence_assessment_ranges():
    assessment = EvidenceAssessment(
        decision="sufficient",
        coverage_score=0.95,
        quality_score=0.90,
        confidence=0.92,
        reason_code="full_coverage",
    )
    assert assessment.decision == "sufficient"

    with pytest.raises(ValidationError):
        EvidenceAssessment(
            decision="sufficient",
            coverage_score=1.5,  # must be <= 1.0
            quality_score=0.9,
            confidence=0.8,
            reason_code="invalid",
        )


def test_evidence_assessment_terminal_decisions():
    valid_decisions = ["sufficient", "insufficient", "conflicting", "clarification", "abstain"]
    for dec in valid_decisions:
        ass = EvidenceAssessment(
            decision=dec,  # type: ignore
            coverage_score=0.5,
            quality_score=0.5,
            confidence=0.5,
            reason_code="test",
        )
        assert ass.decision == dec


def test_tool_result_approval_boundary():
    # Unapproved side-effect result
    res = ToolResult(
        tool_name="send_email",
        status="unapproved",
        error="Explicit user approval required for side-effect tool",
        requires_approval=True,
    )
    assert res.status == "unapproved"
    assert res.requires_approval is True
    assert res.result is None


def test_answer_citations():
    ans = Answer(
        answer_text="Refunds are given within 30 days.",
        citation_ids=["ev_001"],
        confidence=0.95,
        needs_follow_up=False,
    )
    assert ans.citation_ids == ["ev_001"]
    assert ans.confidence == 0.95


def test_no_hidden_chain_of_thought():
    # Ensure Answer and AcquisitionPlan do not expose or require hidden thought fields
    ans = Answer(answer_text="Answer text", citation_ids=[])
    assert not hasattr(ans, "chain_of_thought")
    assert not hasattr(ans, "reasoning_steps")
    plan = AcquisitionPlan(action="vector_search", reason_code="first_pass")
    assert not hasattr(plan, "chain_of_thought")

