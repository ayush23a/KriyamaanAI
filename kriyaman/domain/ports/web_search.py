from typing import Protocol
from domain.models import EvidenceItem, WebSearchRequest


class WebSearchProvider(Protocol):
    def search(self, request: WebSearchRequest) -> list[EvidenceItem]:
        ...

