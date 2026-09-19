from unittest.mock import AsyncMock, MagicMock
import pytest
from adapters.cache.memory import InMemoryCacheAdapter
from application.cache_service import CacheService


@pytest.mark.asyncio
async def test_cache_service_hit_and_miss():
    cache_port = InMemoryCacheAdapter()
    service = CacheService(cache_port=cache_port, session_ttl_seconds=60)

    loader = AsyncMock(return_value={"session_id": "sess_1", "title": "Test Session"})

    # 1. First call: Cache miss -> calls loader
    data1 = await service.get_or_load(
        namespace="session:v1",
        key="sess_1",
        loader=loader,
        ttl_seconds=60,
    )
    assert data1 == {"session_id": "sess_1", "title": "Test Session"}
    assert loader.call_count == 1

    # 2. Second call: Cache hit -> loader NOT called again
    data2 = await service.get_or_load(
        namespace="session:v1",
        key="sess_1",
        loader=loader,
        ttl_seconds=60,
    )
    assert data2 == {"session_id": "sess_1", "title": "Test Session"}
    assert loader.call_count == 1


@pytest.mark.asyncio
async def test_cache_service_fallback_on_cache_error():
    # CachePort returns None on errors (e.g. Redis disconnect)
    cache_port = MagicMock()
    cache_port.get.return_value = None  # simulate cache failure / miss
    cache_port.set.side_effect = Exception("Redis write timeout")  # simulate failed write

    service = CacheService(cache_port=cache_port)
    loader = AsyncMock(return_value=["item1", "item2"])

    data = await service.get_or_load(
        namespace="retrieval:v1",
        key="query_hash",
        loader=loader,
        ttl_seconds=30,
    )

    # Loader executed successfully despite cache failure
    assert data == ["item1", "item2"]
    assert loader.call_count == 1


def test_cache_service_invalidation():
    cache_port = InMemoryCacheAdapter()
    service = CacheService(cache_port=cache_port)

    cache_port.set("session:v1", "sess_1", b"session_data", ttl_seconds=60)
    cache_port.set("messages:v1", "sess_1", b"messages_data", ttl_seconds=60)

    service.invalidate_session("sess_1")

    assert cache_port.get("session:v1", "sess_1") is None
    assert cache_port.get("messages:v1", "sess_1") is None

