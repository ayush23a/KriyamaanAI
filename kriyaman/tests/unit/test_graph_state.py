from domain.models import (
    AcquisitionPlan,
    Answer,
    ContextPackage,
    EvidenceAssessment,
    EvidenceItem,
    ExecutionBudgets,
    ExecutionEvent,
    UsageSnapshot,
)
from application.graph.state import GraphState


def test_graph_state_structure():
    budgets = ExecutionBudgets()
    usage = UsageSnapshot()
    state: GraphState = {
        "run_id": "run_test_123",
        "session_id": "sess_test_456",
        "user_query": "What is the return policy?",
        "normalized_query": "what is the return policy",
        "status": "running",
        "controller_plan": None,
        "plan_history": [],
        "evidence": [],
        "evidence_assessment": None,
        "memory_items": [],
        "tool_results": [],
        "retrieval_iterations": 0,
        "tool_calls": 0,
        "budgets": budgets,
        "usage": usage,
        "execution_events": [],
        "context_package": None,
        "answer": None,
        "failure": None,
    }

    assert state["run_id"] == "run_test_123"
    assert state["status"] == "running"
    assert state["retrieval_iterations"] == 0
    assert state["tool_calls"] == 0


def test_graph_state_terminal_statuses():
    valid_statuses = ["running", "clarification", "answer", "abstention", "conflicting", "failed"]
    for status in valid_statuses:
        state: GraphState = {
            "run_id": "run_1",
            "session_id": "sess_1",
            "user_query": "query",
            "normalized_query": "query",
            "status": status,  # type: ignore
            "controller_plan": None,
            "plan_history": [],
            "evidence": [],
            "evidence_assessment": None,
            "memory_items": [],
            "tool_results": [],
            "retrieval_iterations": 0,
            "tool_calls": 0,
            "budgets": ExecutionBudgets(),
            "usage": UsageSnapshot(),
            "execution_events": [],
            "context_package": None,
            "answer": None,
            "failure": None,
        }
        assert state["status"] == status

