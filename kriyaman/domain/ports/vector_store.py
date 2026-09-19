from typing import Protocol
from domain.models import DocumentChunk, EvidenceItem, VectorSearchRequest


class VectorStore(Protocol):
    def upsert_chunks(self, chunks: list[DocumentChunk]) -> None:
        ...

    def search(self, request: VectorSearchRequest) -> list[EvidenceItem]:
        ...

    def delete_document(self, document_id: str) -> None:
        ...

