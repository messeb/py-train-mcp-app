from __future__ import annotations

import time
from typing import Any


class TTLCache:
    """In-process TTL cache. Thread-safe via GIL for CPython; no locking added."""

    def __init__(self, default_ttl: int = 90) -> None:
        self._default_ttl = default_ttl
        self._store: dict[str, tuple[Any, float]] = {}
        # Value tuple: (data, expires_at_monotonic)

    def get(self, key: str) -> Any | None:
        """Return cached value or None if missing or expired."""
        entry = self._store.get(key)
        if entry is None:
            return None
        data, expires_at = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        return data

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store value with given TTL (seconds). Uses default_ttl when ttl is None."""
        effective_ttl = ttl if ttl is not None else self._default_ttl
        self._store[key] = (value, time.monotonic() + effective_ttl)

    def invalidate(self, key: str) -> None:
        """Remove a specific key immediately."""
        self._store.pop(key, None)

    def clear(self) -> None:
        """Remove all cached entries."""
        self._store.clear()

    def _evict_expired(self) -> None:
        """Remove all expired entries from the store."""
        now = time.monotonic()
        expired_keys = [k for k, (_, exp) in self._store.items() if now > exp]
        for k in expired_keys:
            del self._store[k]
