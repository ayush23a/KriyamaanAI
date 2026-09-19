from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from domain.errors import ValidationError
from application.ingestion_service import IngestionService, MAX_FILE_SIZE_BYTES
from tests.fakes.fake_embeddings import FakeEmbeddingProvider


@pytest.mark.asyncio
async def test_ingest_document_success():
    fake_embedding = FakeEmbeddingProvider(dim=384)
    service = IngestionService(embedding_provider=fake_embedding)

    mock_session = AsyncMock()

    with patch("application.ingestion_service.DocumentRepository") as MockDocRepo, \
         patch("application.ingestion_service.DocumentChunkRepository") as MockChunkRepo:
        
        doc_repo_inst = AsyncMock()
        chunk_repo_inst = AsyncMock()
        MockDocRepo.return_value = doc_repo_inst
        MockChunkRepo.return_value = chunk_repo_inst

        # Simulate no existing document (first ingestion)
        doc_repo_inst.get_by_session_and_hash.return_value = None

        mock_created_doc = MagicMock()
        mock_created_doc.id = "doc_123"
        doc_repo_inst.create.return_value = mock_created_doc

        content = b"This is a test document content that will be parsed and chunked."
        result = await service.ingest_document(
            session=mock_session,
            session_id="sess_1",
            filename="test.txt",
            content=content,
        )

        assert result.session_id == "sess_1"
        assert result.name == "test.txt"
        assert result.is_duplicate is False
        assert result.chunks_count >= 1
        assert doc_repo_inst.create.called
        assert chunk_repo_inst.create_batch.called


@pytest.mark.asyncio
async def test_ingest_document_idempotent_duplicate():
    fake_embedding = FakeEmbeddingProvider(dim=384)
    service = IngestionService(embedding_provider=fake_embedding)

    mock_session = AsyncMock()

    with patch("application.ingestion_service.DocumentRepository") as MockDocRepo, \
         patch("application.ingestion_service.DocumentChunkRepository") as MockChunkRepo:
        
        doc_repo_inst = AsyncMock()
        chunk_repo_inst = AsyncMock()
        MockDocRepo.return_value = doc_repo_inst
        MockChunkRepo.return_value = chunk_repo_inst

        # Simulate existing document found
        mock_existing = MagicMock()
        mock_existing.id = "doc_existing_123"
        mock_existing.session_id = "sess_1"
        mock_existing.name = "test.txt"
        mock_existing.mime_type = "text/plain"
        mock_existing.sha256 = "existing_sha256"
        mock_existing.status = "processed"

        doc_repo_inst.get_by_session_and_hash.return_value = mock_existing
        chunk_repo_inst.list_by_document.return_value = [MagicMock(), MagicMock()]

        content = b"Existing document content."
        result = await service.ingest_document(
            session=mock_session,
            session_id="sess_1",
            filename="test.txt",
            content=content,
        )

        assert result.is_duplicate is True
        assert result.document_id == "doc_existing_123"
        assert result.chunks_count == 2
        # Verify that create was NOT called
        assert not doc_repo_inst.create.called
        assert not chunk_repo_inst.create_batch.called


@pytest.mark.asyncio
async def test_ingest_oversized_file():
    fake_embedding = FakeEmbeddingProvider()
    service = IngestionService(embedding_provider=fake_embedding)
    mock_session = AsyncMock()

    oversized = b"x" * (MAX_FILE_SIZE_BYTES + 10)
    with pytest.raises(ValidationError) as exc:
        await service.ingest_document(
            session=mock_session,
            session_id="sess_1",
            filename="big.txt",
            content=oversized,
        )
    assert "exceeds maximum limit" in str(exc.value)

