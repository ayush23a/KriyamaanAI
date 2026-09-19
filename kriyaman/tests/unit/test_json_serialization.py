from datetime import datetime, timezone
from decimal import Decimal
import json
from unittest.mock import AsyncMock, MagicMock
import uuid
import pytest

from application.run_service import RunExecutionService
from domain.models import (
    Answer,
    EvidenceAssessment,
    ExecutionBudgets,
    UsageSnapshot,
)
from persistence.json_utils import to_json_serializable
from persistence.models import RunModel, SessionModel
from persistence.repositories.run_repo import (
    RetrievalRecordRepository,
    RunEventRepository,
    RunRepository,
    ToolCallRepository,
)


@pytest.mark.asyncio
async def test_run_repository_create_budgets_json_with_decimal():
    """Regression test: verify that RunRepository.create safely converts Decimal in budgets to JSON-serializable types."""
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    repo = RunRepository(mock_session)

    default_budgets = ExecutionBudgets()
    assert isinstance(default_budgets.max_estimated_cost_usd, Decimal)

    # Even if caller passes raw model_dump() with Decimal
    budgets_raw = default_budgets.model_dump()
    assert isinstance(budgets_raw["max_estimated_cost_usd"], Decimal)

    run = await repo.create(
        session_id="sess_123",
        budgets=budgets_raw,
        run_id="run_123",
        status="running",
    )

    # budgets_json must be valid JSON and serializable by json.dumps
    serialized = json.dumps(run.budgets_json)
    assert serialized is not None
    loaded = json.loads(serialized)
    assert loaded["max_estimated_cost_usd"] == str(default_budgets.max_estimated_cost_usd)
    assert loaded["max_retrieval_iterations"] == default_budgets.max_retrieval_iterations


@pytest.mark.asyncio
async def test_run_repository_update_terminal_usage_json_with_decimal():
    """Verify that update_terminal safely serializes Decimal and usage metrics."""
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    repo = RunRepository(mock_session)

    existing_run = RunModel(
        id="run_123",
        session_id="sess_123",
        status="running",
        budgets_json={},
        usage_json={},
    )
    repo.get_by_id = AsyncMock(return_value=existing_run)

    usage = UsageSnapshot(
        retrieval_iterations=2,
        tool_calls=1,
        latency_ms=1200,
        input_tokens=450,
        output_tokens=120,
        estimated_cost_usd=Decimal("0.0035"),
    )
    usage_raw = usage.model_dump()
    assert isinstance(usage_raw["estimated_cost_usd"], Decimal)

    updated_run = await repo.update_terminal(
        run_id="run_123",
        status="completed",
        final_decision="sufficient",
        usage=usage_raw,
    )

    assert updated_run is not None
    serialized = json.dumps(updated_run.usage_json)
    loaded = json.loads(serialized)
    assert loaded["estimated_cost_usd"] == "0.0035"
    assert loaded["latency_ms"] == 1200


@pytest.mark.asyncio
async def test_run_event_repository_payload_json_serialization():
    """Verify that RunEventRepository converts UUID, Decimal, and datetime to valid JSON primitives."""
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    repo = RunEventRepository(mock_session)

    payload = {
        "event_uuid": uuid.uuid4(),
        "cost": Decimal("0.0125"),
        "timestamp": datetime.now(timezone.utc),
        "status": "in_progress",
    }

    event = await repo.append_event(
        run_id="run_123",
        sequence=1,
        event_type="test_event",
        payload=payload,
    )

    serialized = json.dumps(event.payload_json)
    loaded = json.loads(serialized)
    assert loaded["cost"] == "0.0125"
    assert loaded["status"] == "in_progress"
    assert isinstance(loaded["event_uuid"], str)
    assert isinstance(loaded["timestamp"], str)


@pytest.mark.asyncio
async def test_retrieval_record_and_tool_call_json_serialization():
    """Verify that RetrievalRecordRepository and ToolCallRepository safely serialize JSON fields."""
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    retrieval_repo = RetrievalRecordRepository(mock_session)
    tool_repo = ToolCallRepository(mock_session)

    record = await retrieval_repo.create(
        run_id="run_123",
        iteration=1,
        method="hybrid",
        query="test query",
        filters={"min_score": Decimal("0.75"), "tag_id": uuid.uuid4()},
        results=[{"doc_id": "d1", "score": Decimal("0.92")}],
        latency_ms=85,
    )
    assert json.dumps(record.filters_json) is not None
    assert json.dumps(record.results_json) is not None

    call = await tool_repo.create(
        run_id="run_123",
        tool_name="calculator",
        arguments={"amount": Decimal("100.50")},
        result={"tax": Decimal("8.04")},
        status="success",
        latency_ms=25,
    )
    assert json.dumps(call.arguments_json) is not None
    assert json.dumps(call.result_json) is not None


@pytest.mark.asyncio
async def test_run_service_execute_run_persists_default_budgets_json():
    """Verify that RunExecutionService persists default ExecutionBudgets without Decimal JSON serialization errors."""
    mock_db = AsyncMock()
    mock_db.add = MagicMock()

    # Mock session and turns query
    mock_session = SessionModel(
        id="sess_abc",
        memory_principal_id="prin_123",
        title="Test Session",
        metadata_json={},
        created_at=datetime.now(timezone.utc),
    )
    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value.first.return_value = mock_session
    mock_execute_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_execute_result)

    service = RunExecutionService()

    # Mock graph execution
    fake_final_state = {
        "run_id": "run_test_abc",
        "session_id": "sess_abc",
        "status": "answer",
        "execution_events": [],
        "answer": Answer(answer_text="Test answer", citation_ids=[], confidence=1.0),
        "evidence_assessment": EvidenceAssessment(
            decision="sufficient",
            coverage_score=1.0,
            quality_score=1.0,
            confidence=1.0,
            reason_code="ok",
        ),
        "usage": UsageSnapshot(
            retrieval_iterations=1,
            estimated_cost_usd=Decimal("0.002"),
        ),
    }
    service.build_graph = MagicMock(return_value=MagicMock(invoke=MagicMock(return_value=fake_final_state)))

    # Execute with default ExecutionBudgets containing Decimal
    result = await service.execute_run(
        db=mock_db,
        session_id="sess_abc",
        query="What is the policy?",
        budgets=ExecutionBudgets(),
    )

    assert result["status"] == "answer"
    assert mock_db.commit.called

    # Verify that the added run record has JSON-serializable budgets_json with max_estimated_cost_usd
    added_objects = [call[0][0] for call in mock_db.add.call_args_list]
    run_records = [obj for obj in added_objects if isinstance(obj, RunModel)]
    assert len(run_records) >= 1
    run_record = run_records[0]
    serialized = json.dumps(run_record.budgets_json)
    assert serialized is not None
    loaded = json.loads(serialized)
    assert "max_estimated_cost_usd" in loaded
    assert loaded["max_estimated_cost_usd"] == "0.25"

