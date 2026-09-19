from domain.models import EvidenceAssessment, ExecutionBudgets
from application.controller import AgentController
from tests.fakes.fake_tools import FakeToolRegistry


def test_controller_greeting_no_acquisition():
    controller = AgentController()
    plan = controller.decide(
        query="Hello there!",
        normalized_query="hello there",
    )
    assert plan.action == "no_acquisition_required"
    assert plan.reason_code == "conversational_greeting"
    assert plan.expected_information_gain == "low"


def test_controller_tool_call_request():
    registry = FakeToolRegistry()
    controller = AgentController(tool_registry=registry)
    plan = controller.decide(
        query="Please call tool format_text",
        normalized_query="please call tool format_text",
        available_tools=["format_text", "send_email"],
    )
    assert plan.action == "tool_call"
    assert plan.tool_name == "format_text"


def test_controller_default_vector_search():
    controller = AgentController()
    plan = controller.decide(
        query="What is the refund policy?",
        normalized_query="what is the refund policy",
    )
    assert plan.action == "vector_search"
    assert plan.query == "what is the refund policy"
    assert plan.top_k == 5
    assert plan.rerank is True


def test_controller_refine():
    controller = AgentController()
    budgets = ExecutionBudgets(max_retrieval_iterations=3)

    prior_assessment = EvidenceAssessment(
        decision="insufficient",
        coverage_score=0.2,
        quality_score=0.5,
        confidence=0.5,
        missing_aspects=["timeframe", "exceptions"],
        conflict_groups=[],
        reason_code="low_coverage",
    )

    refined = controller.refine(
        query="refund policy",
        prior_assessment=prior_assessment,
        retrieval_iterations=1,
        budgets=budgets,
    )
    assert refined.action == "vector_search"
    assert "timeframe" in refined.query

    # When max iterations reached
    exhausted = controller.refine(
        query="refund policy",
        prior_assessment=prior_assessment,
        retrieval_iterations=3,
        budgets=budgets,
    )
    assert exhausted.action == "abstain"
    assert exhausted.reason_code == "max_iterations_reached"


def test_controller_refine_summary_query():
    controller = AgentController()
    budgets = ExecutionBudgets(max_retrieval_iterations=3)
    prior = EvidenceAssessment(
        decision="insufficient",
        coverage_score=0.2,
        quality_score=0.4,
        confidence=0.5,
        missing_aspects=[],
        reason_code="insufficient_semantic_coverage",
    )
    refined = controller.refine(
        query="what does the uploaded files tell us about?",
        prior_assessment=prior,
        retrieval_iterations=1,
        budgets=budgets,
    )
    assert refined.query == "document summary main findings key points"


def test_controller_refine_advantages_query():
    controller = AgentController()
    budgets = ExecutionBudgets(max_retrieval_iterations=3)
    prior = EvidenceAssessment(
        decision="insufficient",
        coverage_score=0.2,
        quality_score=0.4,
        confidence=0.5,
        missing_aspects=["system_advantages"],
        reason_code="insufficient_semantic_coverage",
    )
    refined = controller.refine(
        query="what are the positive sides or advantages of this system?",
        prior_assessment=prior,
        retrieval_iterations=1,
        budgets=budgets,
    )
    assert refined.query == "system strengths benefits advantages positive findings"


def test_controller_refine_limitations_query():
    controller = AgentController()
    budgets = ExecutionBudgets(max_retrieval_iterations=3)
    prior = EvidenceAssessment(
        decision="insufficient",
        coverage_score=0.2,
        quality_score=0.4,
        confidence=0.5,
        missing_aspects=["system_limitations"],
        reason_code="insufficient_semantic_coverage",
    )
    refined = controller.refine(
        query="what are the limitations?",
        prior_assessment=prior,
        retrieval_iterations=1,
        budgets=budgets,
    )
    assert refined.query == "limitations weaknesses risks problems"


def test_controller_refine_findings_query():
    controller = AgentController()
    budgets = ExecutionBudgets(max_retrieval_iterations=3)
    prior = EvidenceAssessment(
        decision="insufficient",
        coverage_score=0.2,
        quality_score=0.4,
        confidence=0.5,
        missing_aspects=["main_findings"],
        reason_code="insufficient_semantic_coverage",
    )
    refined = controller.refine(
        query="what are the main findings?",
        prior_assessment=prior,
        retrieval_iterations=1,
        budgets=budgets,
    )
    assert refined.query == "main findings results conclusions"


def test_controller_refine_comparison_query():
    controller = AgentController()
    budgets = ExecutionBudgets(max_retrieval_iterations=3)
    prior = EvidenceAssessment(
        decision="insufficient",
        coverage_score=0.2,
        quality_score=0.4,
        confidence=0.5,
        missing_aspects=["cross_document_comparison"],
        reason_code="insufficient_semantic_coverage",
    )
    refined = controller.refine(
        query="compare the two reviews",
        prior_assessment=prior,
        retrieval_iterations=1,
        budgets=budgets,
    )
    assert refined.query == "common findings differences agreements disagreements"


def test_controller_refine_never_appends_stopwords():
    controller = AgentController()
    budgets = ExecutionBudgets(max_retrieval_iterations=3)
    prior = EvidenceAssessment(
        decision="insufficient",
        coverage_score=0.2,
        quality_score=0.4,
        confidence=0.5,
        missing_aspects=["what", "this", "are", "algorithms"],
        reason_code="insufficient_semantic_coverage",
    )
    refined = controller.refine(
        query="quantum computing architecture",
        prior_assessment=prior,
        retrieval_iterations=1,
        budgets=budgets,
    )
    assert "algorithms" in refined.query
    assert not any(sw in refined.query.split() for sw in ["what", "this", "are"])

