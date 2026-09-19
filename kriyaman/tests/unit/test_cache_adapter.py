import time
from unittest.mock import MagicMock
import pytest
import redis
from adapters.cache.memory import InMemoryCacheAdapter
from adapters.cache.redis import MAX_CACHE_VALUE_BYTES, RedisCacheAdapter


def test_in_memory_cache_basic_ops():
    cache = InMemoryCacheAdapter()
    namespace = "session:v1"
    key = "sess_123"
    value = b"serialized_data"

    # Miss initially
    assert cache.get(namespace, key) is None

    # Set and hit
    cache.set(namespace, key, value, ttl_seconds=10)
    assert cache.get(namespace, key) == value

    # Delete
    cache.delete(namespace, key)
    assert cache.get(namespace, key) is None


def test_in_memory_cache_expiration():
    cache = InMemoryCacheAdapter()
    namespace = "session:v1"
    key = "sess_exp"
    value = b"short_lived"

    # Set with 0 or negative TTL (simulating immediate expiration)
    cache.set(namespace, key, value, ttl_seconds=-1)
    assert cache.get(namespace, key) is None


def test_in_memory_cache_delete_namespace():
    cache = InMemoryCacheAdapter()
    cache.set("ns1", "k1", b"val1", ttl_seconds=60)
    cache.set("ns1", "k2", b"val2", ttl_seconds=60)
    cache.set("ns2", "k1", b"val3", ttl_seconds=60)

    cache.delete_namespace("ns1")
    assert cache.get("ns1", "k1") is None
    assert cache.get("ns1", "k2") is None
    assert cache.get("ns2", "k1") == b"val3"


def test_redis_cache_adapter_success():
    mock_client = MagicMock()
    mock_client.get.return_value = b"cached_content"

    adapter = RedisCacheAdapter(client=mock_client)
    res = adapter.get("messages:v1", "key1")
    assert res == b"cached_content"
    mock_client.get.assert_called_once_with("messages:v1:key1")

    adapter.set("messages:v1", "key1", b"new_content", ttl_seconds=60)
    mock_client.set.assert_called_once_with("messages:v1:key1", b"new_content", ex=60)

    adapter.delete("messages:v1", "key1")
    mock_client.delete.assert_called_once_with("messages:v1:key1")


def test_redis_cache_adapter_graceful_fallback_on_connection_error():
    """Verify that Redis connection errors or timeouts degrade gracefully to cache miss (None)."""
    mock_client = MagicMock()
    mock_client.get.side_effect = redis.ConnectionError("Redis connection refused")
    mock_client.set.side_effect = redis.TimeoutError("Redis timed out")
    mock_client.delete.side_effect = redis.RedisError("General redis error")

    adapter = RedisCacheAdapter(client=mock_client)

    # get returns None on error, does not raise
    assert adapter.get("session:v1", "key_error") is None

    # set suppresses error, does not raise
    adapter.set("session:v1", "key_error", b"value", ttl_seconds=30)

    # delete suppresses error, does not raise
    adapter.delete("session:v1", "key_error")


def test_redis_cache_adapter_size_limit():
    mock_client = MagicMock()
    adapter = RedisCacheAdapter(client=mock_client)

    oversized_data = b"x" * (MAX_CACHE_VALUE_BYTES + 10)
    adapter.set("ns", "key", oversized_data, ttl_seconds=60)

    # Should not call client.set because value exceeds MAX_CACHE_VALUE_BYTES
    mock_client.set.assert_not_called()

