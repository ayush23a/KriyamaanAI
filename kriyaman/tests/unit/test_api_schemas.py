from datetime import datetime, timezone
import pytest
from pydantic import ValidationError as PydanticValidationError
from app.api.schemas import (
    AnswerResponse,
    DocumentResponse,
    ErrorDetail,
    ErrorResponse,
    HealthResponse,
    MemoryCreateRequest,
    RunCreateRequest,
    RunResponse,
    SessionCreateRequest,
    SessionResponse,
)


def test_error_envelope_structure():
    err = ErrorResponse(
        error=ErrorDetail(
            code="BUDGET_EXCEEDED",
            message="The run stopped at the configured latency budget.",
            run_id="run_123",
        )
    )
    dump = err.model_dump()
    assert dump["error"]["code"] == "BUDGET_EXCEEDED"
    assert dump["error"]["run_id"] == "run_123"


def test_health_response_schema():
    health = HealthResponse(
        status="healthy",
        version="1.0.0",
        dependencies={"database": "healthy", "cache": "healthy"},
    )
    assert health.status == "healthy"
    assert health.dependencies["database"] == "healthy"


def test_session_schemas():
    req = SessionCreateRequest(title="Test Session", metadata={"env": "test"})
    assert req.title == "Test Session"

    resp = SessionResponse(
        session_id="sess_1",
        memory_principal_id="prin_1",
        title="Test Session",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        metadata={"env": "test"},
    )
    assert resp.session_id == "sess_1"


def test_run_create_request_validation():
    # Valid query
    req = RunCreateRequest(query="What is the refund policy?")
    assert req.query == "What is the refund policy?"
    assert req.enable_web_search is False

    # Empty query should fail validation
    with pytest.raises(PydanticValidationError):
        RunCreateRequest(query="")


def test_memory_create_request_validation():
    req = MemoryCreateRequest(content="User prefers concise responses")
    assert req.kind == "user_preference"

    with pytest.raises(PydanticValidationError):
        MemoryCreateRequest(content="")

