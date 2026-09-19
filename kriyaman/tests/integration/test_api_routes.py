from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest
from httpx import ASGITransport, AsyncClient
from app.dependencies import (
    get_db,
    get_ingestion_service,
    get_run_service,
)
from app.main import app
from application.ingestion_service import IngestionResult
from domain.errors import (
    BudgetExceededError,
    PolicyViolationError,
    ResourceNotFoundError,
)
from domain.models import Answer, EvidenceAssessment, EvidenceItem, ExecutionBudgets, UsageSnapshot
from persistence.models import (
    ConversationTurnModel,
    DocumentModel,
    MemoryModel,
    MemoryPrincipalModel,
    RunEventModel,
    RunModel,
    SessionModel,
)


@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    return session


@pytest.fixture
def async_client(mock_db_session):
    app.dependency_overrides[get_db] = lambda: mock_db_session
    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")
    yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health_endpoint(async_client, mock_db_session):
    resp = await async_client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "dependencies" in data
    assert data["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_create_session(async_client, mock_db_session):
    # Mock Principal and Session creation
    mock_principal = MemoryPrincipalModel(id="prin_123", namespace_key="anon_test")
    mock_session = SessionModel(
        id="sess_456",
        memory_principal_id="prin_123",
        title="My Session",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        metadata_json={},
    )

    # get_or_create principal
    mock_db_session.execute.return_value.scalars.return_value.first.side_effect = [
        mock_principal,  # get_by_namespace_key
        None,
    ]

    # session.add and session.flush mocked
    with pytest.MonkeyPatch.context() as mp:
        from persistence.repositories.principal_repo import MemoryPrincipalRepository
        from persistence.repositories.session_repo import SessionRepository

        async def fake_get_or_create(self, namespace_key, kind="anonymous", metadata=None):
            return mock_principal

        async def fake_create_session(self, memory_principal_id, title=None, metadata=None, session_id=None):
            return mock_session

        mp.setattr(MemoryPrincipalRepository, "get_or_create", fake_get_or_create)
        mp.setattr(SessionRepository, "create", fake_create_session)

        resp = await async_client.post("/api/v1/sessions", json={"title": "My Session"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["session_id"] == "sess_456"
        assert data["memory_principal_id"] == "prin_123"
        assert data["title"] == "My Session"


@pytest.mark.asyncio
async def test_get_session_not_found(async_client, mock_db_session):
    with pytest.MonkeyPatch.context() as mp:
        from persistence.repositories.session_repo import SessionRepository
        mp.setattr(SessionRepository, "get_by_id", AsyncMock(return_value=None))

        resp = await async_client.get("/api/v1/sessions/nonexistent_id")
        assert resp.status_code == 404
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == "RESOURCE_NOT_FOUND"
        assert "nonexistent_id" in data["error"]["message"]


@pytest.mark.asyncio
async def test_get_session_success(async_client, mock_db_session):
    now = datetime.now(timezone.utc)
    mock_session = SessionModel(
        id="sess_1",
        memory_principal_id="prin_1",
        title="Existing Session",
        created_at=now,
        updated_at=now,
        metadata_json={},
    )
    mock_turn = ConversationTurnModel(
        id="turn_1",
        session_id="sess_1",
        run_id="run_1",
        user_query="Hello",
        answer_json={"answer_text": "Hi!", "citation_ids": [], "confidence": 1.0},
        status="completed",
        created_at=now,
    )

    with pytest.MonkeyPatch.context() as mp:
        from persistence.repositories.session_repo import SessionRepository
        from persistence.repositories.turn_repo import ConversationTurnRepository

        async def fake_get(self, session_id):
            return mock_session

        async def fake_list_turns(self, session_id, limit=10):
            return [mock_turn]

        mp.setattr(SessionRepository, "get_by_id", fake_get)
        mp.setattr(ConversationTurnRepository, "list_recent_turns", fake_list_turns)

        resp = await async_client.get("/api/v1/sessions/sess_1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == "sess_1"
        assert len(data["turns"]) == 1
        assert data["turns"][0]["user_query"] == "Hello"


@pytest.mark.asyncio
async def test_create_run_success(async_client, mock_db_session):
    mock_run_service = AsyncMock()
    mock_run_service.execute_run.return_value = {
        "run_id": "run_999",
        "session_id": "sess_1",
        "status": "answer",
        "state": {
            "answer": Answer(
                answer_text="Return is allowed in 30 days.",
                citation_ids=["ev_1"],
                confidence=0.95,
            ),
            "evidence": [
                EvidenceItem(
                    evidence_id="ev_1",
                    source_type="document",
                    source_id="doc_1",
                    content="30 days return.",
                    retrieval_method="vector",
                    retrieval_score=0.92,
                )
            ],
            "evidence_assessment": EvidenceAssessment(
                coverage_score=0.9,
                quality_score=0.9,
                confidence=0.95,
                decision="sufficient",
                reason_code="sufficient_evidence",
            ),
            "budgets": ExecutionBudgets(),
            "usage": UsageSnapshot(prompt_tokens=100, completion_tokens=25),
        },
    }

    app.dependency_overrides[get_run_service] = lambda: mock_run_service

    resp = await async_client.post(
        "/api/v1/sessions/sess_1/runs",
        json={"query": "What is the return policy?", "enable_web_search": False},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["run_id"] == "run_999"
    assert data["status"] == "answer"
    assert data["answer"]["answer_text"] == "Return is allowed in 30 days."
    assert len(data["evidence"]) == 1
    assert data["evidence"][0]["evidence_id"] == "ev_1"
    assert data["poll_url"] == "/api/v1/runs/run_999"
    assert data["events_url"] == "/api/v1/runs/run_999/events"


@pytest.mark.asyncio
async def test_create_run_empty_query_validation(async_client):
    resp = await async_client.post("/api/v1/sessions/sess_1/runs", json={"query": ""})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_run_events(async_client, mock_db_session):
    now = datetime.now(timezone.utc)
    mock_events = [
        RunEventModel(
            id="ev_row_1",
            run_id="run_100",
            sequence=0,
            event_type="run_initialized",
            payload_json={"normalized_query": "hello"},
            created_at=now,
        ),
        RunEventModel(
            id="ev_row_2",
            run_id="run_100",
            sequence=1,
            event_type="answer_generated",
            payload_json={"confidence": 1.0},
            created_at=now,
        ),
    ]

    with pytest.MonkeyPatch.context() as mp:
        from persistence.repositories.run_repo import RunEventRepository

        async def fake_list(self, run_id):
            return mock_events

        mp.setattr(RunEventRepository, "list_by_run", fake_list)

        resp = await async_client.get("/api/v1/runs/run_100/events")
        assert resp.status_code == 200
        data = resp.json()
        assert data["run_id"] == "run_100"
        assert len(data["events"]) == 2
        assert data["events"][0]["event_type"] == "run_initialized"


@pytest.mark.asyncio
async def test_upload_document_success(async_client, mock_db_session):
    mock_session = SessionModel(
        id="sess_1",
        memory_principal_id="prin_1",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    mock_ingestion_service = AsyncMock()
    mock_ingestion_service.ingest_document.return_value = IngestionResult(
        document_id="doc_new_1",
        session_id="sess_1",
        name="policy.txt",
        mime_type="text/plain",
        sha256="abc123hash",
        chunks_count=3,
        is_duplicate=False,
        status="processed",
    )

    app.dependency_overrides[get_ingestion_service] = lambda: mock_ingestion_service

    with pytest.MonkeyPatch.context() as mp:
        from persistence.repositories.session_repo import SessionRepository
        mp.setattr(SessionRepository, "get_by_id", AsyncMock(return_value=mock_session))

        files = {"file": ("policy.txt", b"Company return policy text content.", "text/plain")}
        resp = await async_client.post("/api/v1/sessions/sess_1/documents", files=files)

        assert resp.status_code == 201
        data = resp.json()
        assert data["document_id"] == "doc_new_1"
        assert data["chunk_count"] == 3


@pytest.mark.asyncio
async def test_list_and_delete_documents(async_client, mock_db_session):
    now = datetime.now(timezone.utc)
    mock_docs = [
        DocumentModel(
            id="doc_1",
            session_id="sess_1",
            name="guide.pdf",
            mime_type="application/pdf",
            sha256="h1",
            status="processed",
            created_at=now,
        )
    ]

    with pytest.MonkeyPatch.context() as mp:
        from persistence.repositories.chunk_repo import DocumentChunkRepository
        from persistence.repositories.document_repo import DocumentRepository

        mp.setattr(DocumentRepository, "list_by_session", AsyncMock(return_value=mock_docs))
        mp.setattr(DocumentRepository, "get_by_id", AsyncMock(return_value=mock_docs[0]))
        mp.setattr(DocumentRepository, "delete", AsyncMock(return_value=True))
        mp.setattr(DocumentChunkRepository, "delete_by_document", AsyncMock(return_value=2))

        # List
        list_resp = await async_client.get("/api/v1/sessions/sess_1/documents")
        assert list_resp.status_code == 200
        assert len(list_resp.json()["documents"]) == 1

        # Delete
        del_resp = await async_client.delete("/api/v1/documents/doc_1")
        assert del_resp.status_code == 200
        assert del_resp.json()["success"] is True


@pytest.mark.asyncio
async def test_memories_crud(async_client, mock_db_session):
    now = datetime.now(timezone.utc)
    mock_session = SessionModel(
        id="sess_1",
        memory_principal_id="prin_1",
        created_at=now,
        updated_at=now,
    )
    mock_mem = MemoryModel(
        id="mem_1",
        memory_principal_id="prin_1",
        kind="user_preference",
        content="Prefer short bullet points",
        status="active",
        created_at=now,
    )

    with pytest.MonkeyPatch.context() as mp:
        from persistence.repositories.memory_repo import MemoryRepository
        from persistence.repositories.session_repo import SessionRepository

        mp.setattr(SessionRepository, "get_by_id", AsyncMock(return_value=mock_session))
        mp.setattr(MemoryRepository, "create_explicit", AsyncMock(return_value=mock_mem))
        mp.setattr(MemoryRepository, "list_by_principal", AsyncMock(return_value=[mock_mem]))
        mp.setattr(MemoryRepository, "get_by_id", AsyncMock(return_value=mock_mem))
        mp.setattr(MemoryRepository, "delete", AsyncMock(return_value=True))

        # Create
        create_resp = await async_client.post(
            "/api/v1/sessions/sess_1/memories",
            json={"content": "Prefer short bullet points", "kind": "user_preference"},
        )
        assert create_resp.status_code == 201
        assert create_resp.json()["memory_id"] == "mem_1"

        # List
        list_resp = await async_client.get("/api/v1/sessions/sess_1/memories")
        assert list_resp.status_code == 200
        assert len(list_resp.json()["memories"]) == 1

        # Delete
        del_resp = await async_client.delete("/api/v1/memories/mem_1")
        assert del_resp.status_code == 200
        assert del_resp.json()["success"] is True

