from unittest.mock import MagicMock
from domain.models import DocumentChunk, VectorSearchRequest
from adapters.vectorstores.pgvector import PgVectorStore
from tests.fakes.fake_embeddings import FakeEmbeddingProvider


def test_pgvector_store_upsert_and_delete():
    mock_session = MagicMock()
    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__enter__.return_value = mock_session

    store = PgVectorStore(session_factory=mock_session_factory)

    chunks = [
        DocumentChunk(
            id="chunk_1",
            document_id="doc_1",
            chunk_index=0,
            content="Sample chunk content.",
            content_hash="hash1",
            embedding=[0.1] * 384,
            metadata={"source": "test"},
        )
    ]

    mock_session.execute.return_value.scalars.return_value.first.return_value = None

    # Upsert
    store.upsert_chunks(chunks)
    assert mock_session.add.called

    # Delete
    mock_doc = MagicMock()
    mock_session.execute.return_value.scalars.return_value.first.return_value = mock_doc
    store.delete_document("doc_1")
    assert mock_session.delete.called


def test_pgvector_store_search():
    mock_session = MagicMock()
    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__enter__.return_value = mock_session

    fake_embedding = FakeEmbeddingProvider(dim=384)
    store = PgVectorStore(
        session_factory=mock_session_factory,
        embedding_provider=fake_embedding,
    )

    mock_chunk = MagicMock()
    mock_chunk.id = "chunk_123"
    mock_chunk.content = "Return policy allows 30 days."
    mock_chunk.metadata_json = {"page": 1}

    mock_doc = MagicMock()
    mock_doc.id = "doc_456"
    mock_doc.name = "ReturnPolicy.pdf"

    # distance = 0.15 => similarity score = 1.0 - 0.15 = 0.85
    mock_session.execute.return_value.all.return_value = [(mock_chunk, mock_doc, 0.15)]

    req = VectorSearchRequest(
        query="return policy",
        top_k=5,
        filters={"session_id": "sess_1"},
    )
    results = store.search(req)

    assert len(results) == 1
    ev = results[0]
    assert ev.evidence_id == "ev_chunk_123"
    assert ev.source_type == "document"
    assert ev.document_id == "doc_456"
    assert ev.title == "ReturnPolicy.pdf"
    assert ev.content == "Return policy allows 30 days."
    assert ev.retrieval_method == "pgvector_cosine"
    assert ev.retrieval_score == 0.85

