from typing import Literal
from application.graph.state import GraphState


def check_budgets_exceeded(state: GraphState) -> bool:
    """Check if any of the 6 execution budgets has been exhausted."""
    budgets = state["budgets"]
    usage = state["usage"]

    if state.get("retrieval_iterations", 0) >= budgets.max_retrieval_iterations:
        return True
    if state.get("tool_calls", 0) >= budgets.max_tool_calls:
        return True
    if usage.latency_ms >= budgets.max_latency_ms:
        return True
    if usage.input_tokens >= budgets.max_input_tokens:
        return True
    if usage.output_tokens >= budgets.max_output_tokens:
        return True
    if usage.estimated_cost_usd >= budgets.max_estimated_cost_usd:
        return True
    return False


def route_after_controller(
    state: GraphState,
) -> Literal["clarification_terminal", "abstention_terminal", "acquisition_stage"]:
    """Route after initial controller decision."""
    if check_budgets_exceeded(state):
        return "abstention_terminal"

    plan = state.get("controller_plan")
    if not plan:
        return "acquisition_stage"

    if plan.action == "clarify":
        return "clarification_terminal"
    if plan.action == "abstain":
        return "abstention_terminal"

    return "acquisition_stage"


def route_after_acquisition(
    state: GraphState,
) -> Literal["evidence_judge", "retrieval_agent"]:
    """Route from acquisition_stage to either retrieval_agent or directly to evidence_judge."""
    plan = state.get("controller_plan")
    if plan and plan.action == "no_acquisition_required":
        return "evidence_judge"
    return "retrieval_agent"


def route_after_judge(
    state: GraphState,
) -> Literal[
    "terminal_ready",
    "clarification_terminal",
    "abstention_terminal",
    "controller_refine",
    "conflicting_terminal",
]:
    """Route after Evidence/Sufficiency Judge evaluation."""
    assessment = state.get("evidence_assessment")
    if not assessment:
        return "abstention_terminal"

    decision = assessment.decision
    iterations = state.get("retrieval_iterations", 0)
    max_iterations = state["budgets"].max_retrieval_iterations
    budget_exhausted = check_budgets_exceeded(state)

    if decision == "sufficient":
        return "terminal_ready"

    if decision == "clarification":
        return "clarification_terminal"

    if decision == "abstain":
        return "abstention_terminal"

    if decision == "insufficient":
        if not budget_exhausted and iterations < max_iterations:
            return "controller_refine"
        return "abstention_terminal"

    if decision == "conflicting":
        if not budget_exhausted and iterations < max_iterations:
            return "controller_refine"
        return "conflicting_terminal"

    return "abstention_terminal"
