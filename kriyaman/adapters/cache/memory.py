import time
from domain.ports.cache import CachePort


class InMemoryCacheAdapter(CachePort):
    """In-memory CachePort implementation for tests and local non-redis environments."""

    def __init__(self):
        # Store as: {namespace: {key: (value_bytes, expiry_timestamp)}}
        self._store: dict[str, dict[str, tuple[bytes, float]]] = {}

    def get(self, namespace: str, key: str) -> bytes | None:
        ns_dict = self._store.get(namespace)
        if not ns_dict:
            return None
        item = ns_dict.get(key)
        if not item:
            return None
        value, expiry = item
        if time.time() > expiry:
            del ns_dict[key]
            return None
        return value

    def set(self, namespace: str, key: str, value: bytes, ttl_seconds: int) -> None:
        if namespace not in self._store:
            self._store[namespace] = {}
        expiry = time.time() + ttl_seconds
        self._store[namespace][key] = (value, expiry)

    def delete(self, namespace: str, key: str) -> None:
        ns_dict = self._store.get(namespace)
        if ns_dict and key in ns_dict:
            del ns_dict[key]

    def delete_namespace(self, namespace: str) -> None:
        if namespace in self._store:
            del self._store[namespace]

    def clear(self) -> None:
        self._store.clear()

