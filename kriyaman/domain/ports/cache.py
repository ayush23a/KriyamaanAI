from typing import Protocol


class CachePort(Protocol):
    def get(self, namespace: str, key: str) -> bytes | None:
        """Retrieve cached bytes for a namespace and key, or None on miss or failure."""
        ...

    def set(self, namespace: str, key: str, value: bytes, ttl_seconds: int) -> None:
        """Store bytes under namespace and key with a bounded TTL."""
        ...

    def delete(self, namespace: str, key: str) -> None:
        """Remove a cached entry."""
        ...

    def delete_namespace(self, namespace: str) -> None:
        """Remove all entries belonging to a namespace."""
        ...

