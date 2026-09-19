import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from domain.models import DocumentChunk, ExecutionBudgets, UsageSnapshot
from application.controller import AgentController
from application.evidence_judge import EvidenceJudge
from application.graph.builder import create_kriyaman_graph
from application.graph.nodes import GraphNodes
from application.graph.state import GraphState
from application.retrieval_agent import RetrievalAgent
from persistence.checkpoint import PostgresCheckpointSaver
from persistence.models import (
    LangGraphBlobModel,
    LangGraphCheckpointModel,
    LangGraphWriteModel,
)
from tests.fakes.fake_vector_store import FakeVectorStore


from sqlalchemy.pool import StaticPool


def _create_sqlite_checkpoint_saver():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    LangGraphCheckpointModel.__table__.create(engine)
    LangGraphBlobModel.__table__.create(engine)
    LangGraphWriteModel.__table__.create(engine)
    factory = sessionmaker(bind=engine)
    return PostgresCheckpointSaver(session_factory=factory), factory


def test_postgres_checkpoint_saver_crud():
    saver, factory = _create_sqlite_checkpoint_saver()

    config = {
        "configurable": {
            "thread_id": "thread_1",
            "checkpoint_ns": "",
            "checkpoint_id": "cp_1",
        }
    }
    checkpoint = {
        "v": 1,
        "id": "cp_1",
        "ts": "2026-09-18T00:00:00Z",
        "channel_values": {"status": "running", "counter": 42},
        "channel_versions": {"status": 1, "counter": 1},
        "versions_seen": {},
    }
    metadata = {"step": 1, "source": "input"}
    new_versions = {"status": 1, "counter": 1}

    # 1. Put
    saved_config = saver.put(config, checkpoint, metadata, new_versions)
    assert saved_config["configurable"]["checkpoint_id"] == "cp_1"

    # 2. Get tuple
    retrieved = saver.get_tuple(config)
    assert retrieved is not None
    assert retrieved.checkpoint["id"] == "cp_1"
    assert retrieved.checkpoint["channel_values"]["status"] == "running"
    assert retrieved.checkpoint["channel_values"]["counter"] == 42
    assert retrieved.metadata["step"] == 1

    # 3. Put writes
    saver.put_writes(config, [("channel_msg", "Hello world")], task_id="task_1")
    retrieved_with_writes = saver.get_tuple(config)
    assert len(retrieved_with_writes.pending_writes) == 1
    assert retrieved_with_writes.pending_writes[0][1] == "channel_msg"
    assert retrieved_with_writes.pending_writes[0][2] == "Hello world"

    # 4. List
    tuples = list(saver.list(config))
    assert len(tuples) >= 1
    assert tuples[0].checkpoint["id"] == "cp_1"

    # 5. Delete thread
    saver.delete_thread("thread_1")
    assert saver.get_tuple(config) is None


def test_workflow_checkpoint_persistence_and_resume():
    """Verify that a full LangGraph run persists checkpoints to the database and can be resumed."""
    saver, factory = _create_sqlite_checkpoint_saver()

    store = FakeVectorStore()
    store.upsert_chunks([
        DocumentChunk(
            id="c1",
            document_id="doc_1",
            chunk_index=0,
            content="Full refund within 30 days of purchase.",
            content_hash="h1",
        )
    ])

    ctrl = AgentController()
    judge = EvidenceJudge()
    retrieval_agent = RetrievalAgent(vector_store=store)

    nodes = GraphNodes(
        controller=ctrl,
        retrieval_agent=retrieval_agent,
        evidence_judge=judge,
    )

    graph = create_kriyaman_graph(nodes=nodes, checkpointer=saver)

    initial_state: GraphState = {
        "run_id": "run_check_1",
        "session_id": "sess_check_1",
        "user_query": "What is the refund window?",
        "normalized_query": "what is the refund window",
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

    thread_id = "thread_resume_test_100"
    config = {"configurable": {"thread_id": thread_id}}

    # Execute run
    final_state = graph.invoke(initial_state, config=config)
    assert final_state["status"] == "abstention" or final_state["status"] == "answer"

    # Now verify durability: create a brand-new saver pointing to the same storage
    fresh_saver = PostgresCheckpointSaver(session_factory=factory)
    persisted_tuple = fresh_saver.get_tuple(config)

    assert persisted_tuple is not None
    assert persisted_tuple.checkpoint["channel_values"]["run_id"] == "run_check_1"
    assert persisted_tuple.checkpoint["channel_values"]["normalized_query"] == "What is the refund window?"
    assert len(persisted_tuple.checkpoint["channel_values"]["execution_events"]) > 0

    # Resume graph execution using the restored checkpoint state
    restored_graph = create_kriyaman_graph(nodes=nodes, checkpointer=fresh_saver)
    current_graph_state = restored_graph.get_state(config)
    assert current_graph_state.values["run_id"] == "run_check_1"

