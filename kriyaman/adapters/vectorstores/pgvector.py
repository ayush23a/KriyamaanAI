from datetime import datetime, timezone
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session
from domain.models import DocumentChunk, EvidenceItem, VectorSearchRequest
from domain.ports.embeddings import EmbeddingProvider
from domain.ports.vector_store import VectorStore
from persistence.db import get_sync_session_factory
from persistence.models import DocumentChunkModel, DocumentModel


class PgVectorStore(VectorStore):
    """PostgreSQL + pgvector implementation of the VectorStore port."""

    def __init__(
        self,
        session_factory=None,
        embedding_provider: EmbeddingProvider | None = None,
    ):
        self._session_factory = session_factory or get_sync_session_factory()
        self._embedding_provider = embedding_provider

    def upsert_chunks(self, chunks: list[DocumentChunk]) -> None:
        if not chunks:
            return

        with self._session_factory() as session:
            with session.begin():
                for chunk in chunks:
                    existing = session.execute(
                        select(DocumentChunkModel).where(DocumentChunkModel.id == chunk.id)
                    ).scalars().first()

                    if existing:
                        existing.content = chunk.content
                        existing.content_hash = chunk.content_hash
                        existing.embedding = chunk.embedding
                        existing.metadata_json = chunk.metadata
                    else:
                        chunk_model = DocumentChunkModel(
                            id=chunk.id,
                            document_id=chunk.document_id,
                            chunk_index=chunk.chunk_index,
                            content=chunk.content,
                            content_hash=chunk.content_hash,
                            embedding=chunk.embedding,
                            metadata_json=chunk.metadata,
                        )
                        session.add(chunk_model)

    def search(self, request: VectorSearchRequest) -> list[EvidenceItem]:
        query_embedding = request.embedding
        if query_embedding is None:
            if self._embedding_provider is None:
                raise ValueError("PgVectorStore requires either request.embedding or an embedding_provider to search.")
            query_embedding = self._embedding_provider.embed_query(request.query)

        with self._session_factory() as session:
            distance_expr = DocumentChunkModel.embedding.cosine_distance(query_embedding).label("distance")

            stmt = (
                select(DocumentChunkModel, DocumentModel, distance_expr)
                .join(DocumentModel, DocumentChunkModel.document_id == DocumentModel.id)
                .where(DocumentChunkModel.embedding.is_not(None))
            )

            # Apply metadata filters
            session_id = request.filters.get("session_id")
            if session_id:
                stmt = stmt.where(DocumentModel.session_id == str(session_id))

            document_id = request.filters.get("document_id")
            if document_id:
                stmt = stmt.where(DocumentChunkModel.document_id == str(document_id))

            stmt = stmt.order_by(distance_expr.asc()).limit(request.top_k)

            rows = session.execute(stmt).all()

            results: list[EvidenceItem] = []
            for chunk_row, doc_row, distance in rows:
                score = max(0.0, min(1.0, 1.0 - float(distance)))
                evidence = EvidenceItem(
                    evidence_id=f"ev_{chunk_row.id}",
                    source_type="document",
                    source_id=doc_row.id,
                    title=doc_row.name,
                    content=chunk_row.content,
                    document_id=doc_row.id,
                    chunk_id=chunk_row.id,
                    metadata=chunk_row.metadata_json,
                    retrieval_method="pgvector_cosine",
                    retrieval_score=round(score, 4),
                    retrieved_at=datetime.now(timezone.utc),
                )
                results.append(evidence)

            return results

    def delete_document(self, document_id: str) -> None:
        with self._session_factory() as session:
            with session.begin():
                doc = session.execute(
                    select(DocumentModel).where(DocumentModel.id == document_id)
                ).scalars().first()
                if doc:
                    session.delete(doc)

