import logging
from pydantic import BaseModel, Field

from application.guardrails.regex_rules import DANGEROUS_EXECUTION_PATTERNS
from domain.models import AcquisitionPlan, ExecutionBudgets, UsageSnapshot
from domain.ports.tools import ToolRegistry

logger = logging.getLogger(__name__)

ALLOWED_ACTIONS = {
    "vector_search",
    "metadata_filter",
    "hybrid_search",
    "web_search",
    "memory_search",
    "tool_call",
    "refine_query",
    "clarify",
    "no_acquisition_required",
    "answer",
    "abstain",
}

RETRIEVAL_ACTIONS = {
    "vector_search",
    "metadata_filter",
    "hybrid_search",
    "web_search",
    "memory_search",
    "refine_query",
}


class PlanValidationResult(BaseModel):
    is_valid: bool
    sanitized_plan: AcquisitionPlan
    errors: list[str] = Field(default_factory=list)
    reason_code: str = "plan_valid"


class PlanValidator:
    """Validates and enforces deterministic execution policies on AcquisitionPlans."""

    def __init__(
        self,
        max_query_length: int = 2000,
        min_top_k: int = 1,
        max_top_k: int = 20,
    ) -> None:
        self.max_query_length = max_query_length
        self.min_top_k = min_top_k
        self.max_top_k = max_top_k

    def validate(
        self,
        plan: AcquisitionPlan,
        tool_registry: ToolRegistry | None = None,
        budgets: ExecutionBudgets | None = None,
        usage: UsageSnapshot | None = None,
        is_tool_approved: bool = False,
        enable_web_search: bool = True,
    ) -> PlanValidationResult:
        errors: list[str] = []
        updates: dict[str, object] = {}

        # 1. Action validation
        if plan.action not in ALLOWED_ACTIONS:
            errors.append(f"Disallowed action: {plan.action}")
            fallback_plan = plan.model_copy(
                update={"action": "abstain", "reason_code": "disallowed_action"}
            )
            return PlanValidationResult(
                is_valid=False,
                sanitized_plan=fallback_plan,
                errors=errors,
                reason_code="invalid_action",
            )

        if not enable_web_search and plan.action == "web_search":
            errors.append("Web search is disabled for this session/run")
            fallback_plan = plan.model_copy(
                update={"action": "vector_search", "filters": {}, "reason_code": "web_search_disabled"}
            )
            return PlanValidationResult(
                is_valid=False,
                sanitized_plan=fallback_plan,
                errors=errors,
                reason_code="web_search_disabled",
            )

        if plan.action == "web_search" and plan.filters:
            updates["filters"] = {}

        # 2. Parameter bounds (top_k clamping)
        clamped_top_k = max(self.min_top_k, min(self.max_top_k, plan.top_k))
        if plan.top_k != clamped_top_k:
            updates["top_k"] = clamped_top_k

        # 3. Query constraints
        if plan.action in RETRIEVAL_ACTIONS:
            if not plan.query or not plan.query.strip():
                errors.append("Retrieval action requires a non-empty query")
                fallback_plan = plan.model_copy(
                    update={"action": "abstain", "reason_code": "empty_retrieval_query"}
                )
                return PlanValidationResult(
                    is_valid=False,
                    sanitized_plan=fallback_plan,
                    errors=errors,
                    reason_code="empty_query",
                )
            elif len(plan.query) > self.max_query_length:
                updates["query"] = plan.query[: self.max_query_length]

            # Dangerous pattern check in query
            for pattern in DANGEROUS_EXECUTION_PATTERNS:
                if pattern.search(plan.query):
                    errors.append("Dangerous pattern detected in plan query")
                    fallback_plan = plan.model_copy(
                        update={"action": "abstain", "reason_code": "dangerous_query"}
                    )
                    return PlanValidationResult(
                        is_valid=False,
                        sanitized_plan=fallback_plan,
                        errors=errors,
                        reason_code="dangerous_query",
                    )

        # 4. Tool call checks
        if plan.action == "tool_call":
            if not plan.tool_name or not plan.tool_name.strip():
                errors.append("Tool call requires tool_name")
                fallback_plan = plan.model_copy(
                    update={"action": "abstain", "reason_code": "missing_tool_name"}
                )
                return PlanValidationResult(
                    is_valid=False,
                    sanitized_plan=fallback_plan,
                    errors=errors,
                    reason_code="missing_tool_name",
                )

            if tool_registry is not None:
                available = {t.name: t for t in tool_registry.describe_available()}
                if plan.tool_name not in available:
                    errors.append(f"Tool '{plan.tool_name}' is not registered in ToolRegistry")
                    fallback_plan = plan.model_copy(
                        update={"action": "abstain", "reason_code": "unregistered_tool"}
                    )
                    return PlanValidationResult(
                        is_valid=False,
                        sanitized_plan=fallback_plan,
                        errors=errors,
                        reason_code="unregistered_tool",
                    )
                descriptor = available[plan.tool_name]
                if descriptor.is_side_effect and not is_tool_approved:
                    errors.append(
                        f"Tool '{plan.tool_name}' requires explicit user approval before execution"
                    )
                    fallback_plan = plan.model_copy(
                        update={"action": "abstain", "reason_code": "unapproved_side_effect"}
                    )
                    return PlanValidationResult(
                        is_valid=False,
                        sanitized_plan=fallback_plan,
                        errors=errors,
                        reason_code="unapproved_side_effect",
                    )

            # Check dangerous patterns in arguments
            args_str = str(plan.tool_arguments)
            for pattern in DANGEROUS_EXECUTION_PATTERNS:
                if pattern.search(args_str):
                    errors.append("Dangerous pattern detected in tool arguments")
                    fallback_plan = plan.model_copy(
                        update={"action": "abstain", "reason_code": "dangerous_tool_arguments"}
                    )
                    return PlanValidationResult(
                        is_valid=False,
                        sanitized_plan=fallback_plan,
                        errors=errors,
                        reason_code="dangerous_tool_arguments",
                    )

        # 5. Budget checks
        if budgets is not None and usage is not None:
            if (
                plan.action in RETRIEVAL_ACTIONS
                and usage.retrieval_iterations >= budgets.max_retrieval_iterations
            ):
                errors.append("Max retrieval iterations budget reached")
                fallback_plan = plan.model_copy(
                    update={"action": "abstain", "reason_code": "budget_exhausted"}
                )
                return PlanValidationResult(
                    is_valid=False,
                    sanitized_plan=fallback_plan,
                    errors=errors,
                    reason_code="budget_exhausted",
                )
            if plan.action == "tool_call" and usage.tool_calls >= budgets.max_tool_calls:
                errors.append("Max tool calls budget reached")
                fallback_plan = plan.model_copy(
                    update={"action": "abstain", "reason_code": "budget_exhausted"}
                )
                return PlanValidationResult(
                    is_valid=False,
                    sanitized_plan=fallback_plan,
                    errors=errors,
                    reason_code="budget_exhausted",
                )

        sanitized_plan = plan.model_copy(update=updates) if updates else plan
        return PlanValidationResult(
            is_valid=True,
            sanitized_plan=sanitized_plan,
            errors=errors,
            reason_code="plan_valid",
        )

