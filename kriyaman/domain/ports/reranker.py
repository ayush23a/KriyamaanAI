from typing import Protocol
from domain.models import EvidenceItem


class Reranker(Protocol):
    def rerank(self, query: str, items: list[EvidenceItem], top_k: int) -> list[EvidenceItem]:
        ...

