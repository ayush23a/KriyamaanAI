from decimal import Decimal

from application.plan_validator import PlanValidator
from domain.models import AcquisitionPlan, ExecutionBudgets, ToolDescriptor, UsageSnapshot
from tests.fakes.fake_tools import FakeToolRegistry


def test_plan_validator_allowed_actions():
    validator = PlanValidator()
    valid_plan = AcquisitionPlan(action="vector_search", query="refund policy", top_k=5, reason_code="search")
    res = validator.validate(valid_plan)
    assert res.is_valid is True
    assert res.sanitized_plan.action == "vector_search"

    # Disallowed action
    invalid_plan = AcquisitionPlan.model_construct(
        action="shell_exec",
        query="echo test",
        top_k=5,
        reason_code="invalid",
    )
    res = validator.validate(invalid_plan)
    assert res.is_valid is False
    assert res.reason_code == "invalid_action"
    assert res.sanitized_plan.action == "abstain"


def test_plan_validator_parameter_bounds():
    validator = PlanValidator(min_top_k=1, max_top_k=20)

    # top_k too low -> clamped to min
    low_plan = AcquisitionPlan(action="vector_search", query="test", top_k=0, reason_code="test")
    res = validator.validate(low_plan)
    assert res.is_valid is True
    assert res.sanitized_plan.top_k == 1

    # top_k too high -> clamped to max
    high_plan = AcquisitionPlan(action="vector_search", query="test", top_k=100, reason_code="test")
    res = validator.validate(high_plan)
    assert res.is_valid is True
    assert res.sanitized_plan.top_k == 20


def test_plan_validator_query_constraints():
    validator = PlanValidator(max_query_length=50)

    # Empty query for retrieval action -> invalid
    empty_plan = AcquisitionPlan(action="vector_search", query="   ", reason_code="empty")
    res = validator.validate(empty_plan)
    assert res.is_valid is False
    assert res.reason_code == "empty_query"
    assert res.sanitized_plan.action == "abstain"

    # Truncation for long query
    long_plan = AcquisitionPlan(action="vector_search", query="a" * 100, reason_code="long")
    res = validator.validate(long_plan)
    assert res.is_valid is True
    assert len(res.sanitized_plan.query) == 50

    # Dangerous query
    danger_plan = AcquisitionPlan(
        action="vector_search",
        query="what is the policy; DROP TABLE users;",
        reason_code="danger",
    )
    res = validator.validate(danger_plan)
    assert res.is_valid is False
    assert res.reason_code == "dangerous_query"
    assert res.sanitized_plan.action == "abstain"


def test_plan_validator_tool_call():
    validator = PlanValidator()
    registry = FakeToolRegistry()

    # Missing tool_name
    no_tool_plan = AcquisitionPlan(action="tool_call", tool_name=None, reason_code="test")
    res = validator.validate(no_tool_plan, tool_registry=registry)
    assert res.is_valid is False
    assert res.reason_code == "missing_tool_name"

    # Unregistered tool
    unreg_plan = AcquisitionPlan(action="tool_call", tool_name="unknown_tool", reason_code="test")
    res = validator.validate(unreg_plan, tool_registry=registry)
    assert res.is_valid is False
    assert res.reason_code == "unregistered_tool"

    # Registered read tool
    reg_plan = AcquisitionPlan(action="tool_call", tool_name="format_text", reason_code="test")
    res = validator.validate(reg_plan, tool_registry=registry)
    assert res.is_valid is True

    # Side effect tool without approval
    side_plan = AcquisitionPlan(action="tool_call", tool_name="send_email", reason_code="test")
    res = validator.validate(side_plan, tool_registry=registry, is_tool_approved=False)
    assert res.is_valid is False
    assert res.reason_code == "unapproved_side_effect"

    # Side effect tool with approval
    res_approved = validator.validate(side_plan, tool_registry=registry, is_tool_approved=True)
    assert res_approved.is_valid is True

    # Dangerous arguments
    bad_args_plan = AcquisitionPlan(
        action="tool_call",
        tool_name="format_text",
        tool_arguments={"param": "__import__('os').system('ls')"},
        reason_code="test",
    )
    res_bad = validator.validate(bad_args_plan, tool_registry=registry)
    assert res_bad.is_valid is False
    assert res_bad.reason_code == "dangerous_tool_arguments"


def test_plan_validator_budget_exhaustion():
    validator = PlanValidator()
    budgets = ExecutionBudgets(max_retrieval_iterations=2, max_tool_calls=1)

    # Within budget
    usage_ok = UsageSnapshot(retrieval_iterations=1, tool_calls=0)
    plan = AcquisitionPlan(action="vector_search", query="test", reason_code="test")
    res = validator.validate(plan, budgets=budgets, usage=usage_ok)
    assert res.is_valid is True

    # Retrieval exhausted
    usage_exhausted = UsageSnapshot(retrieval_iterations=2, tool_calls=0)
    res_ex = validator.validate(plan, budgets=budgets, usage=usage_exhausted)
    assert res_ex.is_valid is False
    assert res_ex.reason_code == "budget_exhausted"
    assert res_ex.sanitized_plan.action == "abstain"

    # Tool calls exhausted
    tool_plan = AcquisitionPlan(action="tool_call", tool_name="format_text", reason_code="test")
    usage_tool_ex = UsageSnapshot(retrieval_iterations=0, tool_calls=1)
    res_tool = validator.validate(tool_plan, budgets=budgets, usage=usage_tool_ex)
    assert res_tool.is_valid is False
    assert res_tool.reason_code == "budget_exhausted"
