from typing import Literal, TypedDict
from domain.models import (
    AcquisitionPlan,
    Answer,
    ContextPackage,
    EvidenceAssessment,
    EvidenceItem,
    ExecutionBudgets,
    ExecutionEvent,
    FailureInfo,
    MemoryItem,
    ToolResult,
    UsageSnapshot,
)


class GraphState(TypedDict):
    run_id: str
    session_id: str
    user_query: str
    normalized_query: str
    status: Literal["running", "clarification", "answer", "abstention", "conflicting", "failed"]
    controller_plan: AcquisitionPlan | None
    plan_history: list[AcquisitionPlan]
    evidence: list[EvidenceItem]
    evidence_assessment: EvidenceAssessment | None
    memory_items: list[MemoryItem]
    tool_results: list[ToolResult]
    retrieval_iterations: int
    tool_calls: int
    budgets: ExecutionBudgets
    usage: UsageSnapshot
    execution_events: list[ExecutionEvent]
    context_package: ContextPackage | None
    answer: Answer | None
    failure: FailureInfo | None
    guardrail_rejected: bool
    guardrail_reason_code: str | None
    session_documents: list[str] | None

