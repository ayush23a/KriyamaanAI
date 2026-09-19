from domain.models import AcquisitionPlan, DocumentChunk, EvidenceItem
from application.retrieval_agent import RetrievalAgent
from tests.fakes.fake_tools import FakeToolRegistry
from tests.fakes.fake_vector_store import FakeVectorStore


def test_retrieval_agent_vector_search():
    store = FakeVectorStore()
    store.upsert_chunks([
        DocumentChunk(
            id="c1",
            document_id="d1",
            chunk_index=0,
            content="Document text regarding return policy.",
            content_hash="h1",
        )
    ])

    agent = RetrievalAgent(vector_store=store)
    plan = AcquisitionPlan(
        action="vector_search",
        query="return policy",
        top_k=2,
        reason_code="test",
    )

    evidence, tool_results = agent.execute(
        plan=plan,
        session_id="sess_1",
        run_id="run_1",
        memory_principal_id="p1",
    )

    assert len(evidence) == 1
    assert evidence[0].document_id == "d1"
    assert "return policy" in evidence[0].content
    assert tool_results == []


def test_retrieval_agent_deduplication():
    store = FakeVectorStore()
    store.upsert_chunks([
        DocumentChunk(id="c1", document_id="d1", chunk_index=0, content="Duplicate content", content_hash="h1"),
    ])

    existing_evidence = [
        EvidenceItem(
            evidence_id="ev_existing",
            source_type="document",
            source_id="d1",
            content="Duplicate content",
            retrieval_method="vector",
            retrieval_score=0.9,
        )
    ]

    agent = RetrievalAgent(vector_store=store)
    plan = AcquisitionPlan(action="vector_search", query="test", reason_code="test")

    new_evidence, _ = agent.execute(
        plan=plan,
        session_id="sess_1",
        run_id="run_1",
        memory_principal_id="p1",
        existing_evidence=existing_evidence,
    )

    # Identical content is deduplicated
    assert len(new_evidence) == 0


def test_retrieval_agent_tool_execution():
    registry = FakeToolRegistry()
    agent = RetrievalAgent(tool_registry=registry)

    # 1. Read-only tool
    plan = AcquisitionPlan(
        action="tool_call",
        tool_name="format_text",
        tool_arguments={"text": "lowercase text"},
        reason_code="format",
    )
    evidence, tool_results = agent.execute(
        plan=plan,
        session_id="sess_1",
        run_id="run_1",
        memory_principal_id="p1",
    )
    assert len(tool_results) == 1
    assert tool_results[0].status == "success"
    assert tool_results[0].result == "LOWERCASE TEXT"
    assert len(evidence) == 1
    assert evidence[0].source_type == "tool"

    # 2. Side-effect tool without approval
    side_effect_plan = AcquisitionPlan(
        action="tool_call",
        tool_name="send_email",
        tool_arguments={"recipient": "user@example.com"},
        reason_code="email",
    )
    _, side_results = agent.execute(
        plan=side_effect_plan,
        session_id="sess_1",
        run_id="run_1",
        memory_principal_id="p1",
        is_tool_approved=False,
    )
    assert side_results[0].status == "unapproved"
    assert side_results[0].requires_approval is True

