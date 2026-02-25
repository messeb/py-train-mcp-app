"""Tests for the TTL cache."""
from __future__ import annotations

import time
from unittest.mock import patch

from db_mcp.infrastructure.cache import TTLCache


def test_cache_miss_returns_none() -> None:
    cache = TTLCache()
    assert cache.get("absent") is None


def test_get_miss() -> None:
    cache = TTLCache()
    assert cache.get("nonexistent") is None


def test_cache_hit() -> None:
    cache = TTLCache()
    cache.set("key", "value")
    assert cache.get("key") == "value"


def test_set_and_get() -> None:
    cache = TTLCache()
    cache.set("mykey", {"data": 42})
    assert cache.get("mykey") == {"data": 42}


def test_cache_expiry() -> None:
    """After TTL seconds, get returns None."""
    cache = TTLCache(default_ttl=1)
    cache.set("key", "value")
    # Advance time past TTL using monotonic mock
    with patch("db_mcp.infrastructure.cache.time") as mock_time:
        mock_time.monotonic.return_value = time.monotonic() + 2.0
        assert cache.get("key") is None


def test_cache_expires() -> None:
    """Cache expires after TTL — using time mock."""
    cache = TTLCache(default_ttl=90)
    base_time = 1000.0
    with patch("db_mcp.infrastructure.cache.time") as mock_time:
        mock_time.monotonic.return_value = base_time
        cache.set("k", "v")
        mock_time.monotonic.return_value = base_time + 91.0
        assert cache.get("k") is None


def test_cache_custom_ttl() -> None:
    """Entry with ttl=300 is still live after 91 seconds (default TTL would have expired)."""
    cache = TTLCache(default_ttl=90)
    base_time = 1000.0
    with patch("db_mcp.infrastructure.cache.time") as mock_time:
        mock_time.monotonic.return_value = base_time
        cache.set("k", "v", ttl=300)
        mock_time.monotonic.return_value = base_time + 91.0
        assert cache.get("k") == "v"


def test_cache_set_overwrites() -> None:
    cache = TTLCache()
    cache.set("key", "original")
    cache.set("key", "updated")
    assert cache.get("key") == "updated"


def test_cache_invalidate() -> None:
    cache = TTLCache()
    cache.set("key", "value")
    cache.invalidate("key")
    assert cache.get("key") is None


def test_cache_clear() -> None:
    cache = TTLCache()
    cache.set("k1", "v1")
    cache.set("k2", "v2")
    cache.clear()
    assert cache.get("k1") is None
    assert cache.get("k2") is None


def test_cache_prevents_second_call() -> None:
    """Cache prevents re-fetching the same data (verified via call counting)."""
    cache = TTLCache(default_ttl=90)
    call_count = 0

    def expensive_operation() -> dict:  # type: ignore[type-arg]
        nonlocal call_count
        call_count += 1
        return {"result": call_count}

    # First call — miss
    result = cache.get("op")
    if result is None:
        result = expensive_operation()
        cache.set("op", result)

    # Second call — should hit cache
    result2 = cache.get("op")
    if result2 is None:
        result2 = expensive_operation()
        cache.set("op", result2)

    assert call_count == 1
    assert result2 == {"result": 1}
