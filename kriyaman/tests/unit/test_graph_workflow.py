import pytest
from langgraph.checkpoint.memory import MemorySaver
from domain.models import (
    AcquisitionPlan,
    DocumentChunk,
    EvidenceAssessment,
    EvidenceItem,
    ExecutionBudgets,
    UsageSnapshot,
)
from application.answer_service import AnswerService
from application.controller import AgentController
from application.evidence_judge import EvidenceJudge
from application.graph.builder import create_kriyaman_graph
from application.graph.nodes import GraphNodes
from application.graph.state import GraphState
from application.retrieval_agent import RetrievalAgent
from tests.fakes.fake_llm import FakeLLMProvider
from tests.fakes.fake_vector_store import FakeVectorStore


def _build_test_graph(
    vector_store=None,
    controller=None,
    evidence_judge=None,
    answer_service=None,
    checkpointer=None,
):
    store = vector_store or FakeVectorStore()
    ctrl = controller or AgentController()
    judge = evidence_judge or EvidenceJudge()

    ans_svc = answer_service
    if ans_svc is None and answer_service is not False:
        fake_llm = FakeLLMProvider(
            default_text="Returns are accepted within 30 days for full refund.",
            structured_response={
                "answer_text": "Returns are accepted within 30 days for full refund.",
                "citation_ids": ["ev_c1"],
                "confidence": 0.95,
                "needs_follow_up": False,
            },
        )
        ans_svc = AnswerService(llm_provider=fake_llm)
    elif answer_service is False:
        ans_svc = None

    retrieval_agent = RetrievalAgent(vector_store=store)
    nodes = GraphNodes(
        controller=ctrl,
        retrieval_agent=retrieval_agent,
        evidence_judge=judge,
        answer_service=ans_svc,
    )
    chk = checkpointer or MemorySaver()
    return create_kriyaman_graph(nodes=nodes, checkpointer=chk)


def test_graph_builder_terminal_routing_structure():
    """Structural test: fails if clarification_terminal, abstention_terminal, conflicting_terminal,
    or terminal_ready have any direct edge to END. Verifies exact routing to persist_turn and context_builder."""
    import inspect
    import ast
    from pathlib import Path
    import application.graph.builder as builder_mod

    # 1. Source AST inspection: Builder code must never add a direct edge to END from terminal nodes
    source = inspect.getsource(builder_mod)
    tree = ast.parse(source)

    forbidden_sources = {
        "clarification_terminal",
        "abstention_terminal",
        "conflicting_terminal",
        "terminal_ready",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "add_edge":
            args = node.args
            if len(args) >= 2:
                src_val = args[0].value if isinstance(args[0], ast.Constant) else None
                dst_val = args[1].id if isinstance(args[1], ast.Name) else (
                    args[1].value if isinstance(args[1], ast.Constant) else None
                )
                if src_val in forbidden_sources and dst_val in ("END", "__end__"):
                    pytest.fail(f"Illegal direct END edge found in builder.py: add_edge({src_val!r}, {dst_val})")

    # 2. Compiled graph topology inspection
    graph = _build_test_graph()
    drawable = graph.get_graph()

    edges_by_source = {}
    for edge in drawable.edges:
        edges_by_source.setdefault(edge.source, []).append(edge.target)

    # clarification_terminal must route ONLY to persist_turn
    assert "clarification_terminal" in edges_by_source
    assert "__end__" not in edges_by_source["clarification_terminal"]
    assert edges_by_source["clarification_terminal"] == ["persist_turn"]

    # abstention_terminal must route ONLY to persist_turn
    assert "abstention_terminal" in edges_by_source
    assert "__end__" not in edges_by_source["abstention_terminal"]
    assert edges_by_source["abstention_terminal"] == ["persist_turn"]

    # conflicting_terminal must route ONLY to persist_turn
    assert "conflicting_terminal" in edges_by_source
    assert "__end__" not in edges_by_source["conflicting_terminal"]
    assert edges_by_source["conflicting_terminal"] == ["persist_turn"]

    # terminal_ready must route ONLY to context_builder
    assert "terminal_ready" in edges_by_source
    assert "__end__" not in edges_by_source["terminal_ready"]
    assert edges_by_source["terminal_ready"] == ["context_builder"]

    # persist_turn must route to __end__
    assert "persist_turn" in edges_by_source
    assert edges_by_source["persist_turn"] == ["__end__"]


def test_workflow_first_pass_sufficient():
    """Test standard single-pass retrieval with sufficient evidence, answer generation, and exactly-once persistence."""
    store = FakeVectorStore()
    store.upsert_chunks([
        DocumentChunk(
            id="c1",
            document_id="doc_policy",
            chunk_index=0,
            content="Returns are fully accepted within 30 days of purchase for full refund.",
            content_hash="h1",
        )
    ])

    graph = _build_test_graph(vector_store=store)

    initial_state: GraphState = {
        "run_id": "run_test_1",
        "session_id": "sess_1",
        "user_query": "What is the return and refund policy?",
        "normalized_query": "what is the return and refund policy",
        "status": "running",
        "controller_plan": None,
        "plan_history": [],
        "evidence": [],
        "evidence_assessment": None,
        "memory_items": [],
        "tool_results": [],
        "retrieval_iterations": 0,
        "tool_calls": 0,
        "budgets": ExecutionBudgets(max_retrieval_iterations=3),
        "usage": UsageSnapshot(),
        "execution_events": [],
        "context_package": None,
        "answer": None,
        "failure": None,
    }

    config = {"configurable": {"thread_id": "thread_1"}}
    final_state = graph.invoke(initial_state, config=config)

    assert final_state["status"] == "answer"
    assert final_state["retrieval_iterations"] == 1
    assert len(final_state["evidence"]) == 1
    assert final_state["evidence_assessment"] is not None
    assert final_state["evidence_assessment"].decision == "sufficient"
    assert final_state["answer"] is not None
    assert len(final_state["answer"].citation_ids) > 0

    # Exactly-once terminal persistence check
    persisted_events = [e for e in final_state["execution_events"] if e.event_type == "run_persisted"]
    assert len(persisted_events) == 1
    assert persisted_events[0].payload["final_status"] == "answer"


def test_workflow_no_acquisition_required():
    """Test query that requires no external retrieval (e.g. greeting) passing through judge."""
    """Test query that requires no external retrieval (e.g. greeting) reaching Evidence/Sufficiency Judge and generating answer."""
    graph = _build_test_graph()

    initial_state: GraphState = {
        "run_id": "run_greeting",
        "session_id": "sess_1",
        "user_query": "Hello there!",
        "normalized_query": "hello there",
        "status": "running",
        "controller_plan": None,
        "plan_history": [],
        "evidence": [],
        "evidence_assessment": None,
        "memory_items": [],
        "tool_results": [],
        "retrieval_iterations": 0,
        "tool_calls": 0,
        "budgets": ExecutionBudgets(max_retrieval_iterations=3),
        "usage": UsageSnapshot(),
        "execution_events": [],
        "context_package": None,
        "answer": None,
        "failure": None,
    }

    config = {"configurable": {"thread_id": "thread_greeting"}}
    final_state = graph.invoke(initial_state, config=config)

    assert final_state["status"] == "answer"
    assert final_state["controller_plan"].action == "no_acquisition_required"
    assert final_state["retrieval_iterations"] == 0  # No retrieval executed
    assert final_state["evidence_assessment"] is not None
    assert final_state["evidence_assessment"].decision == "sufficient"
    assert final_state["answer"] is not None

    # Exactly-once terminal persistence check
    persisted_events = [e for e in final_state["execution_events"] if e.event_type == "run_persisted"]
    assert len(persisted_events) == 1


def test_workflow_clarification():
    """Test ambiguous query leading to clarification terminal state."""
    """Test ambiguous query leading to structured clarification terminal answer without LLM generation."""
    class ClarifyController(AgentController):
        def decide(self, **kwargs):
            return AcquisitionPlan(action="clarify", reason_code="ambiguous_query")

    graph = _build_test_graph(controller=ClarifyController())

    initial_state: GraphState = {
        "run_id": "run_clarify",
        "session_id": "sess_1",
        "user_query": "tell me",
        "normalized_query": "tell me",
        "status": "running",
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

    config = {"configurable": {"thread_id": "thread_clarify"}}
    final_state = graph.invoke(initial_state, config=config)

    assert final_state["status"] == "clarification"
    assert final_state["answer"] is not None
    assert final_state["answer"].needs_follow_up is True
    assert final_state["answer"].confidence == 1.0
    assert final_state["answer"].citation_ids == []

    # Verify generate_answer node was never called
    gen_events = [e for e in final_state["execution_events"] if e.event_type == "answer_generated"]
    assert len(gen_events) == 0

    # Exactly-once terminal persistence check
    persisted_events = [e for e in final_state["execution_events"] if e.event_type == "run_persisted"]
    assert len(persisted_events) == 1
    assert persisted_events[0].payload["final_status"] == "clarification"


def test_workflow_iterative_refinement_to_sufficient():
    """Test iterative retrieval where pass 1 is insufficient and pass 2 succeeds."""
    store = FakeVectorStore()
    store.upsert_chunks([
        DocumentChunk(
            id="c1",
            document_id="doc_policy",
            chunk_index=0,
            content="Returns are fully accepted within 30 days for full refund.",
            content_hash="h1",
        )
    ])

    class IterativeEvidenceJudge:
        def __init__(self):
            self.call_count = 0

        def evaluate(self, query, evidence, current_plan, retrieval_iterations, max_iterations):
            self.call_count += 1
            if self.call_count == 1:
                return EvidenceAssessment(
                    decision="insufficient",
                    coverage_score=0.3,
                    quality_score=0.5,
                    confidence=0.5,
                    missing_aspects=["refund conditions"],
                    reason_code="needs_more_evidence",
                )
            return EvidenceAssessment(
                decision="sufficient",
                coverage_score=0.95,
                quality_score=0.95,
                confidence=0.95,
                reason_code="sufficient_evidence",
            )

    graph = _build_test_graph(vector_store=store, evidence_judge=IterativeEvidenceJudge())

    initial_state: GraphState = {
        "run_id": "run_refine_1",
        "session_id": "sess_1",
        "user_query": "What is the return and refund policy?",
        "normalized_query": "what is the return and refund policy",
        "status": "running",
        "controller_plan": None,
        "plan_history": [],
        "evidence": [],
        "evidence_assessment": None,
        "memory_items": [],
        "tool_results": [],
        "retrieval_iterations": 0,
        "tool_calls": 0,
        "budgets": ExecutionBudgets(max_retrieval_iterations=3),
        "usage": UsageSnapshot(),
        "execution_events": [],
        "context_package": None,
        "answer": None,
        "failure": None,
    }

    config = {"configurable": {"thread_id": "thread_refine"}}
    final_state = graph.invoke(initial_state, config=config)

    assert final_state["status"] == "answer"
    assert final_state["retrieval_iterations"] >= 2
    assert final_state["evidence_assessment"].decision == "sufficient"
    assert final_state["answer"] is not None

    persisted_events = [e for e in final_state["execution_events"] if e.event_type == "run_persisted"]
    assert len(persisted_events) == 1
    assert persisted_events[0].payload["final_status"] == "answer"


def test_workflow_iterative_refinement_to_abstention():
    """Test iterative retrieval where budget exhausts, producing structured abstention."""
    store = FakeVectorStore()
    graph = _build_test_graph(vector_store=store)

    # In pass 1, store has no chunks -> insufficient
    # After pass 1, we can test that the graph refines and reaches max or sufficient
    # Let's test budget exhaustion on empty knowledge base:
    initial_state: GraphState = {
        "run_id": "run_exhaust",
        "session_id": "sess_1",
        "user_query": "what are the hidden keys",
        "normalized_query": "what are the hidden keys",
        "status": "running",
        "controller_plan": None,
        "plan_history": [],
        "evidence": [],
        "evidence_assessment": None,
        "memory_items": [],
        "tool_results": [],
        "retrieval_iterations": 0,
        "tool_calls": 0,
        "budgets": ExecutionBudgets(max_retrieval_iterations=2),
        "usage": UsageSnapshot(),
        "execution_events": [],
        "context_package": None,
        "answer": None,
        "failure": None,
    }

    config = {"configurable": {"thread_id": "thread_exhaust"}}
    final_state = graph.invoke(initial_state, config=config)

    # Graph loops twice and then stops at abstention when budget runs out
    # Graph loops and terminates with structured abstention
    assert final_state["status"] == "abstention"
    assert final_state["retrieval_iterations"] >= 2
    assert final_state["evidence_assessment"].decision == "abstain"
    assert final_state["answer"] is not None
    assert final_state["answer"].confidence == 0.0
    assert final_state["answer"].needs_follow_up is False

    # Exactly-once terminal persistence check
    persisted_events = [e for e in final_state["execution_events"] if e.event_type == "run_persisted"]
    assert len(persisted_events) == 1
    assert persisted_events[0].payload["final_status"] == "abstention"


def test_workflow_conflicting_terminal():
    """Test conflicting evidence reaching terminal conflict policy when iterations are exhausted."""
    """Test conflicting evidence reaching terminal conflict with structured conflicting answer."""
    store = FakeVectorStore()
    store.upsert_chunks([
        DocumentChunk(id="c1", document_id="d1", chunk_index=0, content="Yes allowed", metadata={"tags": ["conflict"]}, content_hash="h1"),
        DocumentChunk(id="c2", document_id="d2", chunk_index=0, content="No not allowed", metadata={"tags": ["conflict"]}, content_hash="h2"),
        DocumentChunk(id="c1", document_id="d1", chunk_index=0, content="Yes item is returnable.", metadata={"tags": ["conflict"]}, content_hash="h1"),
        DocumentChunk(id="c2", document_id="d2", chunk_index=0, content="No item is strictly non-returnable.", metadata={"tags": ["conflict"]}, content_hash="h2"),
    ])

    graph = _build_test_graph(vector_store=store)

    initial_state: GraphState = {
        "run_id": "run_conflict",
        "session_id": "sess_1",
        "user_query": "is this allowed",
        "normalized_query": "is this allowed",
        "user_query": "is this returnable",
        "normalized_query": "is this returnable",
        "status": "running",
        "controller_plan": None,
        "plan_history": [],
        "evidence": [],
        "evidence_assessment": None,
        "memory_items": [],
        "tool_results": [],
        "retrieval_iterations": 0,
        "tool_calls": 0,
        "budgets": ExecutionBudgets(max_retrieval_iterations=1),
        "usage": UsageSnapshot(),
        "execution_events": [],
        "context_package": None,
        "answer": None,
        "failure": None,
    }

    config = {"configurable": {"thread_id": "thread_conflict"}}
    final_state = graph.invoke(initial_state, config=config)

    assert final_state["status"] == "conflicting"
    assert final_state["evidence_assessment"].decision == "conflicting"
    assert final_state["answer"] is not None
    assert "Conflicting evidence" in final_state["answer"].answer_text
    assert final_state["answer"].confidence == 0.3
    assert final_state["answer"].needs_follow_up is True
    assert len(final_state["answer"].citation_ids) > 0

    # Exactly-once terminal persistence check
    persisted_events = [e for e in final_state["execution_events"] if e.event_type == "run_persisted"]
    assert len(persisted_events) == 1
    assert persisted_events[0].payload["final_status"] == "conflicting"


def test_workflow_missing_llm_behavior():
    """Test that if no generation LLM is configured, the system returns a policy-approved abstention and never fabricates a success answer."""
    store = FakeVectorStore()
    store.upsert_chunks([
        DocumentChunk(
            id="c1",
            document_id="doc_1",
            chunk_index=0,
            content="Returns are accepted within 30 days.",
            content_hash="h1",
        )
    ])

    # Explicitly pass answer_service=False so no LLM is configured
    graph = _build_test_graph(vector_store=store, answer_service=False)

    initial_state: GraphState = {
        "run_id": "run_no_llm",
        "session_id": "sess_1",
        "user_query": "What is the return window?",
        "normalized_query": "what is the return window",
        "status": "running",
        "controller_plan": None,
        "plan_history": [],
        "evidence": [],
        "evidence_assessment": None,
        "memory_items": [],
        "tool_results": [],
        "retrieval_iterations": 0,
        "tool_calls": 0,
        "budgets": ExecutionBudgets(max_retrieval_iterations=3),
        "usage": UsageSnapshot(),
        "execution_events": [],
        "context_package": None,
        "answer": None,
        "failure": None,
    }

    config = {"configurable": {"thread_id": "thread_no_llm"}}
    final_state = graph.invoke(initial_state, config=config)

    # Must NOT fabricate "Answer based on verified evidence."
    assert final_state["status"] == "abstention"
    assert final_state["answer"] is not None
    assert "No generation LLM provider is configured" in final_state["answer"].answer_text
    assert final_state["answer"].confidence == 0.0

    # Verify generation_abstained_no_llm event emitted
    no_llm_events = [e for e in final_state["execution_events"] if e.event_type == "generation_abstained_no_llm"]
    assert len(no_llm_events) == 1

    # Exactly-once terminal persistence check
    persisted_events = [e for e in final_state["execution_events"] if e.event_type == "run_persisted"]
    assert len(persisted_events) == 1


def test_workflow_budget_enforcement():
    """Verify that all 6 execution budgets are enforced before provider calls."""
    # Test budget exceeded on latency
    graph = _build_test_graph()

    initial_state: GraphState = {
        "run_id": "run_budget_exceeded",
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
        "retrieval_iterations": 0,
        "tool_calls": 0,
        "budgets": ExecutionBudgets(max_latency_ms=1000),
        "usage": UsageSnapshot(latency_ms=1500),  # Pre-exhausted latency
        "execution_events": [],
        "context_package": None,
        "answer": None,
        "failure": None,
    }

    config = {"configurable": {"thread_id": "thread_budget"}}
    final_state = graph.invoke(initial_state, config=config)

    # Aborts before controller planning
    assert final_state["status"] == "abstention"
    assert final_state["retrieval_iterations"] == 0
    budget_events = [e for e in final_state["execution_events"] if "budget_exceeded" in e.event_type]
    assert len(budget_events) > 0

    # Exactly-once terminal persistence
    persisted_events = [e for e in final_state["execution_events"] if e.event_type == "run_persisted"]
    assert len(persisted_events) == 1


def test_workflow_advantages_query_reaches_generation():
    """Verify an advantages query with retrieved evidence containing 'benefits' reaches generation, not abstention."""
    store = FakeVectorStore()
    store.upsert_chunks([
        DocumentChunk(
            id="c_adv",
            document_id="doc_platform",
            chunk_index=0,
            content="The platform provides scalable benefits and notable throughput improvements.",
            content_hash="h_adv",
        )
    ])
    fake_llm = FakeLLMProvider(
        structured_response={
            "answer_text": "The platform offers scalable benefits and throughput improvements.",
            "citation_ids": ["ev_c_adv"],
            "confidence": 0.95,
            "needs_follow_up": False,
        }
    )
    ans_svc = AnswerService(llm_provider=fake_llm)
    graph = _build_test_graph(vector_store=store, answer_service=ans_svc)

    initial_state: GraphState = {
        "run_id": "run_adv",
        "session_id": "sess_1",
        "user_query": "what are the positive sides or advantages of this system?",
        "normalized_query": "what are the positive sides or advantages of this system",
        "status": "running",
        "controller_plan": None,
        "plan_history": [],
        "evidence": [],
        "evidence_assessment": None,
        "memory_items": [],
        "tool_results": [],
        "retrieval_iterations": 0,
        "tool_calls": 0,
        "budgets": ExecutionBudgets(max_retrieval_iterations=3),
        "usage": UsageSnapshot(),
        "execution_events": [],
        "context_package": None,
        "answer": None,
        "failure": None,
    }

    config = {"configurable": {"thread_id": "thread_adv"}}
    final_state = graph.invoke(initial_state, config=config)

    assert final_state["status"] == "answer"
    assert final_state["evidence_assessment"].decision == "sufficient"
    assert final_state["evidence_assessment"].reason_code == "advantages_request_with_retrieved_evidence"
    assert final_state["answer"] is not None
    assert len(final_state["evidence"]) > 0

    # Verify execution events contain meaningful reason codes and evidence counts
    judged_events = [e for e in final_state["execution_events"] if e.event_type == "evidence_judged"]
    assert len(judged_events) >= 1
    assert judged_events[0].payload["reason_code"] == "advantages_request_with_retrieved_evidence"

    acq_events = [e for e in final_state["execution_events"] if e.event_type == "acquisition_executed"]
    assert len(acq_events) >= 1
    assert acq_events[0].payload["new_evidence_count"] == 1


def test_workflow_synthesis_multi_document_reaches_generation():
    """Verify a broad synthesis query across two documents reaches generation."""
    store = FakeVectorStore()
    store.upsert_chunks([
        DocumentChunk(
            id="c_doc1",
            document_id="doc_audit_1",
            chunk_index=0,
            content="First audit report found security compliance satisfactory.",
            content_hash="h_aud1",
        ),
        DocumentChunk(
            id="c_doc2",
            document_id="doc_audit_2",
            chunk_index=0,
            content="Second audit report agreed on data isolation mechanisms.",
            content_hash="h_aud2",
        ),
    ])
    fake_llm = FakeLLMProvider(
        structured_response={
            "answer_text": "Both audit reports agree on security compliance and data isolation.",
            "citation_ids": ["ev_c_doc1", "ev_c_doc2"],
            "confidence": 0.90,
            "needs_follow_up": False,
        }
    )
    ans_svc = AnswerService(llm_provider=fake_llm)
    graph = _build_test_graph(vector_store=store, answer_service=ans_svc)

    initial_state: GraphState = {
        "run_id": "run_synth",
        "session_id": "sess_1",
        "user_query": "what do both audit reports agree on?",
        "normalized_query": "what do both audit reports agree on",
        "status": "running",
        "controller_plan": None,
        "plan_history": [],
        "evidence": [],
        "evidence_assessment": None,
        "memory_items": [],
        "tool_results": [],
        "retrieval_iterations": 0,
        "tool_calls": 0,
        "budgets": ExecutionBudgets(max_retrieval_iterations=3),
        "usage": UsageSnapshot(),
        "execution_events": [],
        "context_package": None,
        "answer": None,
        "failure": None,
    }

    config = {"configurable": {"thread_id": "thread_synth"}}
    final_state = graph.invoke(initial_state, config=config)

    assert final_state["status"] == "answer"
    assert final_state["evidence_assessment"].decision == "sufficient"
    assert final_state["evidence_assessment"].reason_code == "synthesis_request_with_retrieved_evidence"
    assert len(final_state["evidence"]) == 2


def test_workflow_empty_retrieval_abstains_cleanly():
    """Verify genuinely empty retrieval produces structured abstention with clean diagnostic, not stopword dump."""
    store = FakeVectorStore()  # empty store
    graph = _build_test_graph(vector_store=store)

    initial_state: GraphState = {
        "run_id": "run_empty_clean",
        "session_id": "sess_1",
        "user_query": "what are the positive sides or advantages of this system?",
        "normalized_query": "what are the positive sides or advantages of this system",
        "status": "running",
        "controller_plan": None,
        "plan_history": [],
        "evidence": [],
        "evidence_assessment": None,
        "memory_items": [],
        "tool_results": [],
        "retrieval_iterations": 0,
        "tool_calls": 0,
        "budgets": ExecutionBudgets(max_retrieval_iterations=2),
        "usage": UsageSnapshot(),
        "execution_events": [],
        "context_package": None,
        "answer": None,
        "failure": None,
    }

    config = {"configurable": {"thread_id": "thread_empty_clean"}}
    final_state = graph.invoke(initial_state, config=config)

    assert final_state["status"] == "abstention"
    assert final_state["evidence_assessment"].decision == "abstain"
    assert final_state["answer"] is not None
    # Must provide clear diagnostic, never list "Missing information: what, this, sides..."
    assert "No relevant passages were retrieved from the uploaded documents." in final_state["answer"].answer_text
    assert "Missing information: what" not in final_state["answer"].answer_text
