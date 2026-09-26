from datetime import datetime, timezone
from typing import Any
from sqlalchemy import func, select
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

            document_name = request.filters.get("document_name")
            if document_name:
                doc_stmt = stmt.where(DocumentModel.name.ilike(f"%{document_name}%")).order_by(distance_expr.asc()).limit(request.top_k)
                rows = session.execute(doc_stmt).all()
                if not rows:
                    rows = session.execute(stmt.order_by(distance_expr.asc()).limit(request.top_k)).all()
            else:
                rows = session.execute(stmt.order_by(distance_expr.asc()).limit(request.top_k)).all()

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

    def hybrid_search(self, request: VectorSearchRequest) -> list[EvidenceItem]:
        """Hybrid search combining pgvector dense cosine similarity and PostgreSQL full-text search with RRF."""
        candidate_k = max(request.top_k * 4, 20)

        # 1. Fetch dense candidates
        dense_req = VectorSearchRequest(
            query=request.query,
            embedding=request.embedding,
            top_k=candidate_k,
            filters=request.filters,
        )
        dense_items = self.search(dense_req)

        # 2. Fetch sparse full-text candidates
        sparse_items: list[tuple[Any, Any, float]] = []
        if request.query and request.query.strip():
            with self._session_factory() as session:
                clean_q = request.query.strip()
                to_tsv = func.to_tsvector("english", DocumentChunkModel.content)
                plain_q = func.plainto_tsquery("english", clean_q)
                ts_rank = func.ts_rank_cd(to_tsv, plain_q).label("ts_rank")

                stmt = (
                    select(DocumentChunkModel, DocumentModel, ts_rank)
                    .join(DocumentModel, DocumentChunkModel.document_id == DocumentModel.id)
                    .where(to_tsv.op("@@")(plain_q))
                )

                session_id = request.filters.get("session_id")
                if session_id:
                    stmt = stmt.where(DocumentModel.session_id == str(session_id))

                document_id = request.filters.get("document_id")
                if document_id:
                    stmt = stmt.where(DocumentChunkModel.document_id == str(document_id))

                document_name = request.filters.get("document_name")
                if document_name:
                    doc_stmt = (
                        stmt.where(DocumentModel.name.ilike(f"%{document_name}%"))
                        .order_by(ts_rank.desc())
                        .limit(candidate_k)
                    )
                    rows = session.execute(doc_stmt).all()
                    if not rows:
                        rows = session.execute(stmt.order_by(ts_rank.desc()).limit(candidate_k)).all()
                else:
                    rows = session.execute(stmt.order_by(ts_rank.desc()).limit(candidate_k)).all()

                sparse_items = rows

        # 3. Reciprocal Rank Fusion (RRF with k=60)
        K = 60.0
        rrf_scores: dict[str, float] = {}
        item_map: dict[str, EvidenceItem] = {}

        for rank, item in enumerate(dense_items, start=1):
            chunk_id = item.chunk_id or item.evidence_id
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + (1.0 / (K + rank))
            item_map[chunk_id] = item

        for rank, (chunk_row, doc_row, rank_score) in enumerate(sparse_items, start=1):
            chunk_id = chunk_row.id
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + (1.0 / (K + rank))
            if chunk_id not in item_map:
                item_map[chunk_id] = EvidenceItem(
                    evidence_id=f"ev_{chunk_row.id}",
                    source_type="document",
                    source_id=doc_row.id,
                    title=doc_row.name,
                    content=chunk_row.content,
                    document_id=doc_row.id,
                    chunk_id=chunk_row.id,
                    metadata=chunk_row.metadata_json,
                    retrieval_method="postgres_fts",
                    retrieval_score=round(float(rank_score or 0.0), 4),
                    retrieved_at=datetime.now(timezone.utc),
                )

        fused = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        results: list[EvidenceItem] = []
        for chunk_id, score in fused[: request.top_k]:
            evidence = item_map[chunk_id].model_copy(
                update={
                    "retrieval_method": "hybrid_rrf",
                    "retrieval_score": round(min(1.0, score * 30.0), 4),
                }
            )
            results.append(evidence)

        if not results:
            return dense_items[: request.top_k]

        return results

    def delete_document(self, document_id: str) -> None:
        with self._session_factory() as session:
            with session.begin():
                doc = session.execute(
                    select(DocumentModel).where(DocumentModel.id == document_id)
                ).scalars().first()
                if doc:
                    session.delete(doc)

