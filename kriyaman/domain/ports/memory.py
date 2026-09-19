from typing import Protocol
from domain.models import ExplicitMemoryRequest, MemoryItem, MemorySearchRequest


class MemoryStore(Protocol):
    def load_session(self, session_id: str, limit: int = 10) -> list[MemoryItem]:
        ...

    def search_long_term(self, request: MemorySearchRequest) -> list[MemoryItem]:
        ...

    def save_explicit(self, item: ExplicitMemoryRequest) -> MemoryItem:
        ...

