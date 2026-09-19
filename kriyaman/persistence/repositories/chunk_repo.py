from typing import Any, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from persistence.models import DocumentChunkModel, DocumentModel


class DocumentChunkRepository:
    """Repository for document chunk storage and pgvector similarity search."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_batch(self, chunks: list[DocumentChunkModel]) -> list[DocumentChunkModel]:
        self.session.add_all(chunks)
        await self.session.flush()
        return chunks

    async def list_by_document(self, document_id: str) -> Sequence[DocumentChunkModel]:
        result = await self.session.execute(
            select(DocumentChunkModel)
            .where(DocumentChunkModel.document_id == document_id)
            .order_by(DocumentChunkModel.chunk_index.asc())
        )
        return result.scalars().all()

    async def search_similar(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        session_id: str | None = None,
        document_id: str | None = None,
    ) -> list[tuple[DocumentChunkModel, DocumentModel, float]]:
        """Perform cosine similarity search on document chunks using pgvector.

        Returns tuples of (chunk, document, similarity_score).
        """
        # pgvector cosine distance operator: <=>
        # cosine_distance: 0 (identical) to 2 (opposite). similarity = 1 - distance
        distance_expr = DocumentChunkModel.embedding.cosine_distance(query_embedding).label("distance")

        stmt = (
            select(DocumentChunkModel, DocumentModel, distance_expr)
            .join(DocumentModel, DocumentChunkModel.document_id == DocumentModel.id)
            .where(DocumentChunkModel.embedding.is_not(None))
        )

        if session_id:
            stmt = stmt.where(DocumentModel.session_id == session_id)
        if document_id:
            stmt = stmt.where(DocumentChunkModel.document_id == document_id)

        stmt = stmt.order_by(distance_expr.asc()).limit(top_k)

        result = await self.session.execute(stmt)
        rows = result.all()

        results: list[tuple[DocumentChunkModel, DocumentModel, float]] = []
        for chunk, doc, distance in rows:
            # Convert cosine distance to similarity score
            score = max(0.0, min(1.0, 1.0 - float(distance)))
            results.append((chunk, doc, score))

        return results

    async def delete_by_document(self, document_id: str) -> int:
        chunks = await self.list_by_document(document_id)
        count = len(chunks)
        for chunk in chunks:
            await self.session.delete(chunk)
        await self.session.flush()
        return count

