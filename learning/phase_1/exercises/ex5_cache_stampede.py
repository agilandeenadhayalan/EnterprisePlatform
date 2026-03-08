"""
Exercise 5: Cache Stampede Prevention
=======================================

Implement a mutex-based cache stampede prevention strategy.

The problem: When a popular cache key expires, hundreds of concurrent
requests all try to recompute the value simultaneously, overwhelming
the database.

Your solution: Use a lock so only ONE request recomputes while
others wait for the fresh cached value.
"""

import threading
import time
from learning.phase_1.src.m05_caching.cache import CacheAside


class StampedeProtectedCache(CacheAside):
    """
    Cache with mutex-based stampede prevention.

    When a cache miss occurs:
    1. First request acquires a lock and recomputes
    2. Other requests wait for the lock
    3. When lock is released, waiting requests read the fresh cache
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._locks: dict[str, threading.Lock] = {}

    def get_or_load_protected(self, key: str, loader: callable,
                               ttl: float | None = None) -> any:
        """
        Get from cache with stampede protection.

        Steps:
        1. Try cache first (fast path)
        2. If miss, acquire a per-key lock
        3. Double-check cache (another thread may have loaded it)
        4. If still miss, call loader and cache the result
        5. Release lock

        The lock should be per-key (not global) so different keys
        don't block each other.
        """
        # TODO: Implement stampede-protected get (~12 lines)
        raise NotImplementedError("Implement stampede-protected cache")


# ── Tests ──


def test_single_thread_works():
    cache = StampedeProtectedCache(default_ttl=60.0)
    calls = 0

    def loader():
        nonlocal calls
        calls += 1
        return "value"

    result = cache.get_or_load_protected("k1", loader)
    assert result == "value"
    assert calls == 1


def test_second_call_uses_cache():
    cache = StampedeProtectedCache(default_ttl=60.0)
    calls = 0

    def loader():
        nonlocal calls
        calls += 1
        return "value"

    cache.get_or_load_protected("k1", loader)
    cache.get_or_load_protected("k1", loader)
    assert calls == 1  # Loader called only once
