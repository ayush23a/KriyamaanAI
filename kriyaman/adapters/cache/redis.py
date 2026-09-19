import logging
from typing import Any
import redis
from domain.ports.cache import CachePort

logger = logging.getLogger(__name__)

MAX_CACHE_VALUE_BYTES = 5 * 1024 * 1024  # 5MB serialization limit


class RedisCacheAdapter(CachePort):
    """Redis cache adapter adhering to CachePort.

    Fail-safe: timeouts, connection errors, and malformed data are treated
    as cache misses and logged with structured warnings. PostgreSQL fallback is guaranteed.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        socket_timeout: float = 2.0,
        socket_connect_timeout: float = 2.0,
        client: redis.Redis | None = None,
    ):
        self.redis_url = redis_url
        self._client = client or redis.Redis.from_url(
            redis_url,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_connect_timeout,
            decode_responses=False,
        )

    def _format_key(self, namespace: str, key: str) -> str:
        return f"{namespace}:{key}"

    def get(self, namespace: str, key: str) -> bytes | None:
        full_key = self._format_key(namespace, key)
        try:
            val = self._client.get(full_key)
            if val is None:
                return None
            if isinstance(val, bytes):
                return val
            if isinstance(val, str):
                return val.encode("utf-8")
            return None
        except (redis.RedisError, TimeoutError, ConnectionError) as exc:
            logger.warning(
                "Redis get failed for namespace=%s key=%s. Falling back to primary storage. Error: %s",
                namespace,
                key,
                str(exc),
            )
            return None

    def set(self, namespace: str, key: str, value: bytes, ttl_seconds: int) -> None:
        if len(value) > MAX_CACHE_VALUE_BYTES:
            logger.warning(
                "Redis set skipped: value size %d bytes exceeds limit %d bytes for key %s",
                len(value),
                MAX_CACHE_VALUE_BYTES,
                key,
            )
            return

        full_key = self._format_key(namespace, key)
        try:
            self._client.set(full_key, value, ex=ttl_seconds)
        except (redis.RedisError, TimeoutError, ConnectionError) as exc:
            logger.warning(
                "Redis set failed for namespace=%s key=%s. Error: %s",
                namespace,
                key,
                str(exc),
            )

    def delete(self, namespace: str, key: str) -> None:
        full_key = self._format_key(namespace, key)
        try:
            self._client.delete(full_key)
        except (redis.RedisError, TimeoutError, ConnectionError) as exc:
            logger.warning(
                "Redis delete failed for namespace=%s key=%s. Error: %s",
                namespace,
                key,
                str(exc),
            )

    def delete_namespace(self, namespace: str) -> None:
        pattern = f"{namespace}:*"
        try:
            cursor = 0
            while True:
                cursor, keys = self._client.scan(cursor=cursor, match=pattern, count=100)
                if keys:
                    self._client.delete(*keys)
                if cursor == 0:
                    break
        except (redis.RedisError, TimeoutError, ConnectionError) as exc:
            logger.warning(
                "Redis delete_namespace failed for namespace=%s. Error: %s",
                namespace,
                str(exc),
            )

