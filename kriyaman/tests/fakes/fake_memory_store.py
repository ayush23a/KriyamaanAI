from datetime import datetime, timezone
import uuid
from domain.models import ExplicitMemoryRequest, MemoryItem, MemorySearchRequest
from domain.ports.memory import MemoryStore


class FakeMemoryStore(MemoryStore):
    """In-memory fake memory store for tests."""

    def __init__(self):
        self.session_memories: dict[str, list[MemoryItem]] = {}
        self.long_term_memories: list[MemoryItem] = []

    def load_session(self, session_id: str, limit: int = 10) -> list[MemoryItem]:
        items = self.session_memories.get(session_id, [])
        return items[-limit:]

    def search_long_term(self, request: MemorySearchRequest) -> list[MemoryItem]:
        matches = [
            m for m in self.long_term_memories
            if m.memory_principal_id == request.memory_principal_id
        ]
        return matches[: request.top_k]

    def save_explicit(self, item: ExplicitMemoryRequest) -> MemoryItem:
        mem = MemoryItem(
            id=str(uuid.uuid4()),
            memory_principal_id=item.memory_principal_id,
            kind=item.kind,
            content=item.content,
            metadata=item.metadata,
            created_at=datetime.now(timezone.utc),
        )
        self.long_term_memories.append(mem)
        return mem

