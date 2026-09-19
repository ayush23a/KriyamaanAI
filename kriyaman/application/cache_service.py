import hashlib
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar
from domain.ports.cache import CachePort

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CacheService:
    """Cache-aside service wrapping CachePort with guaranteed persistence fallback."""

    def __init__(
        self,
        cache_port: CachePort,
        session_ttl_seconds: int = 300,
        retrieval_ttl_seconds: int = 120,
    ):
        self.cache_port = cache_port
        self.session_ttl_seconds = session_ttl_seconds
        self.retrieval_ttl_seconds = retrieval_ttl_seconds

    def _hash_key(self, raw_key: str) -> str:
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:32]

    async def get_or_load(
        self,
        namespace: str,
        key: str,
        loader: Callable[[], Awaitable[T]],
        ttl_seconds: int,
        serializer: Callable[[T], bytes] | None = None,
        deserializer: Callable[[bytes], T] | None = None,
    ) -> T:
        """Cache-aside read: check cache first; on miss/failure, run loader and populate cache."""
        cached_bytes = self.cache_port.get(namespace, key)
        if cached_bytes is not None:
            try:
                if deserializer:
                    return deserializer(cached_bytes)
                return json.loads(cached_bytes.decode("utf-8"))
            except Exception as exc:
                logger.warning("Failed to deserialize cached data for %s:%s. Error: %s", namespace, key, exc)

        # Cache miss or failure: call authoritative loader (PostgreSQL)
        data = await loader()

        # Best-effort populate cache
        try:
            if serializer:
                payload = serializer(data)
            else:
                payload = json.dumps(data).encode("utf-8")
            self.cache_port.set(namespace, key, payload, ttl_seconds=ttl_seconds)
        except Exception as exc:
            logger.warning("Failed to populate cache for %s:%s. Error: %s", namespace, key, exc)

        return data

    def invalidate_session(self, session_id: str) -> None:
        """Invalidate session metadata and message cache."""
        self.cache_port.delete("session:v1", session_id)
        self.cache_port.delete("messages:v1", session_id)

    def invalidate_retrieval(self, session_id: str) -> None:
        """Invalidate retrieval query cache for a session."""
        self.cache_port.delete_namespace(f"retrieval:v1:{session_id}")

