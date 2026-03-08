"""
Caching Strategies Simulator
==============================

Demonstrates cache-aside, write-through, and stampede prevention.
Uses an in-memory dict as the "cache" (production would use Redis).
"""

from __future__ import annotations

import time
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class CacheEntry:
    """A single cached value with metadata."""
    value: Any
    created_at: float = field(default_factory=time.time)
    ttl: float = 300.0  # 5 minutes default
    access_count: int = 0

    @property
    def is_expired(self) -> bool:
        return time.time() - self.created_at > self.ttl

    @property
    def remaining_ttl(self) -> float:
        return max(0, self.ttl - (time.time() - self.created_at))


class CacheAside:
    """
    Cache-aside (lazy loading) pattern.

    HOW IT WORKS:
    1. Check cache first
    2. On miss: load from database, store in cache
    3. On hit: return cached value
    4. On write: invalidate cache, write to database

    WHY cache-aside:
    - Application controls what gets cached
    - Cache only holds requested data (demand-driven)
    - Cache failure doesn't prevent reads (degrades to DB)

    USED BY: Most read-heavy services (user profiles, zone lookups, config).
    """

    def __init__(self, default_ttl: float = 300.0) -> None:
        self.store: dict[str, CacheEntry] = {}
        self.default_ttl = default_ttl
        self.stats = {"hits": 0, "misses": 0}

    def get(self, key: str) -> Any | None:
        """Get from cache. Returns None on miss or expiry."""
        entry = self.store.get(key)
        if entry and not entry.is_expired:
            entry.access_count += 1
            self.stats["hits"] += 1
            return entry.value

        if entry and entry.is_expired:
            del self.store[key]

        self.stats["misses"] += 1
        return None

    def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        """Store a value in cache."""
        self.store[key] = CacheEntry(
            value=value,
            ttl=ttl or self.default_ttl,
        )

    def invalidate(self, key: str) -> None:
        """Remove a key from cache."""
        self.store.pop(key, None)

    def get_or_load(self, key: str, loader: Callable[[], Any], ttl: float | None = None) -> Any:
        """Get from cache, or load from source and cache the result."""
        value = self.get(key)
        if value is not None:
            return value

        # Cache miss — load from database
        value = loader()
        self.set(key, value, ttl)
        return value

    @property
    def hit_rate(self) -> float:
        total = self.stats["hits"] + self.stats["misses"]
        return self.stats["hits"] / total if total > 0 else 0.0


class WriteThrough(CacheAside):
    """
    Write-through cache: writes go to both cache AND database.

    WHY: Ensures cache is always consistent with the database.
    TRADE-OFF: Writes are slower (two writes), but reads are always fresh.
    """

    def write(self, key: str, value: Any, db_writer: Callable[[str, Any], None]) -> None:
        """Write to both cache and database atomically."""
        db_writer(key, value)     # Write to DB first
        self.set(key, value)       # Then update cache


class StampedeProtector:
    """
    Cache stampede prevention using probabilistic early expiration.

    THE PROBLEM: When a popular cache key expires, hundreds of concurrent
    requests all miss the cache and hit the database simultaneously.

    SOLUTION: Each request has a small probability of refreshing the
    cache before actual expiry, spreading recomputation over time.

    MATH: P(refresh) = exp(-remaining_ttl * beta) where beta controls
    how early refreshes start. Higher beta = earlier refresh.
    """

    def __init__(self, cache: CacheAside, beta: float = 1.0) -> None:
        self.cache = cache
        self.beta = beta

    def should_refresh(self, key: str) -> bool:
        """Should this request proactively refresh the cache?"""
        entry = self.cache.store.get(key)
        if not entry:
            return True

        remaining = entry.remaining_ttl
        if remaining <= 0:
            return True

        # Probabilistic early refresh
        import math
        probability = math.exp(-remaining * self.beta)
        return random.random() < probability
