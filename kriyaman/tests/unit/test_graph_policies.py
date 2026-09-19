from domain.models import (
    AcquisitionPlan,
    EvidenceAssessment,
    ExecutionBudgets,
    UsageSnapshot,
)
from application.graph.policies import (
    check_budgets_exceeded,
    route_after_acquisition,
    route_after_controller,
    route_after_judge,
)
from application.graph.state import GraphState


def _make_dummy_state(**kwargs) -> GraphState:
    base: GraphState = {
        "run_id": "run_1",
        "session_id": "sess_1",
        "user_query": "query",
        "normalized_query": "query",
        "status": "running",
        "controller_plan": None,
        "plan_history": [],
        "evidence": [],
        "evidence_assessment": None,
        "memory_items": [],
        "tool_results": [],
        "retrieval_iterations": 0,
        "tool_calls": 0,
        "budgets": ExecutionBudgets(max_retrieval_iterations=3, max_tool_calls=3, max_latency_ms=30_000),
        "usage": UsageSnapshot(),
        "execution_events": [],
        "context_package": None,
        "answer": None,
        "failure": None,
    }
    base.update(kwargs)  # type: ignore
    return base


def test_route_after_controller():
    # Clarify
    s1 = _make_dummy_state(controller_plan=AcquisitionPlan(action="clarify", reason_code="ambiguous"))
    assert route_after_controller(s1) == "clarification_terminal"

    # Abstain
    s2 = _make_dummy_state(controller_plan=AcquisitionPlan(action="abstain", reason_code="prohibited"))
    assert route_after_controller(s2) == "abstention_terminal"

    # Search
    s3 = _make_dummy_state(controller_plan=AcquisitionPlan(action="vector_search", reason_code="search"))
    assert route_after_controller(s3) == "acquisition_stage"


def test_route_after_acquisition():
    s_no_acq = _make_dummy_state(
        controller_plan=AcquisitionPlan(action="no_acquisition_required", reason_code="greeting")
    )
    assert route_after_acquisition(s_no_acq) == "evidence_judge"

    s_vector = _make_dummy_state(
        controller_plan=AcquisitionPlan(action="vector_search", reason_code="search")
    )
    assert route_after_acquisition(s_vector) == "retrieval_agent"


def test_route_after_judge():
    # Sufficient
    ass_suff = EvidenceAssessment(
        decision="sufficient", coverage_score=0.9, quality_score=0.9, confidence=0.9, reason_code="ok"
    )
    s_suff = _make_dummy_state(evidence_assessment=ass_suff)
    assert route_after_judge(s_suff) == "terminal_ready"

    # Insufficient under budget
    ass_insuff = EvidenceAssessment(
        decision="insufficient", coverage_score=0.2, quality_score=0.5, confidence=0.5, reason_code="miss"
    )
    s_insuff_1 = _make_dummy_state(evidence_assessment=ass_insuff, retrieval_iterations=1)
    assert route_after_judge(s_insuff_1) == "controller_refine"

    # Insufficient budget reached (iterations = 3)
    s_insuff_3 = _make_dummy_state(evidence_assessment=ass_insuff, retrieval_iterations=3)
    assert route_after_judge(s_insuff_3) == "abstention_terminal"

    # Conflicting under budget
    ass_conf = EvidenceAssessment(
        decision="conflicting", coverage_score=0.5, quality_score=0.5, confidence=0.5, reason_code="conflict"
    )
    s_conf_1 = _make_dummy_state(evidence_assessment=ass_conf, retrieval_iterations=1)
    assert route_after_judge(s_conf_1) == "controller_refine"

    # Conflicting budget reached
    s_conf_3 = _make_dummy_state(evidence_assessment=ass_conf, retrieval_iterations=3)
    assert route_after_judge(s_conf_3) == "conflicting_terminal"


def test_budget_exceeded():
    s_ok = _make_dummy_state(retrieval_iterations=1, tool_calls=1)
    assert not check_budgets_exceeded(s_ok)

    s_iter_max = _make_dummy_state(retrieval_iterations=3)
    assert check_budgets_exceeded(s_iter_max)

    s_tool_max = _make_dummy_state(tool_calls=3)
    assert check_budgets_exceeded(s_tool_max)

