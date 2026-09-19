from datetime import datetime, timezone
from domain.models import DocumentChunk, EvidenceItem, VectorSearchRequest
from domain.ports.vector_store import VectorStore


class FakeVectorStore(VectorStore):
    """In-memory fake vector store for tests."""

    def __init__(self):
        self.chunks: dict[str, DocumentChunk] = {}

    def upsert_chunks(self, chunks: list[DocumentChunk]) -> None:
        for chunk in chunks:
            self.chunks[chunk.id] = chunk

    def search(self, request: VectorSearchRequest) -> list[EvidenceItem]:
        results: list[EvidenceItem] = []
        for chunk in list(self.chunks.values())[: request.top_k]:
            results.append(
                EvidenceItem(
                    evidence_id=f"ev_{chunk.id}",
                    source_type="document",
                    source_id=chunk.document_id,
                    title="Fake Document",
                    content=chunk.content,
                    document_id=chunk.document_id,
                    chunk_id=chunk.id,
                    metadata=chunk.metadata,
                    retrieval_method="vector_similarity",
                    retrieval_score=0.95,
                    retrieved_at=datetime.now(timezone.utc),
                )
            )
        return results

    def delete_document(self, document_id: str) -> None:
        to_delete = [
            cid for cid, chunk in self.chunks.items() if chunk.document_id == document_id
        ]
        for cid in to_delete:
            del self.chunks[cid]

