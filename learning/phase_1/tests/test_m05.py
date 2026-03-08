"""Tests for Module 05: Caching Strategies."""

from learning.phase_1.src.m05_caching.cache import (
    CacheAside,
    WriteThrough,
    CacheEntry,
)


class TestCacheAside:
    def test_miss_then_hit(self):
        cache = CacheAside()
        assert cache.get("key1") is None  # Miss
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"  # Hit

    def test_get_or_load(self):
        cache = CacheAside()
        calls = 0

        def loader():
            nonlocal calls
            calls += 1
            return "loaded"

        cache.get_or_load("k1", loader)
        cache.get_or_load("k1", loader)
        assert calls == 1  # Loader called only once

    def test_invalidate(self):
        cache = CacheAside()
        cache.set("k1", "v1")
        cache.invalidate("k1")
        assert cache.get("k1") is None

    def test_hit_rate(self):
        cache = CacheAside()
        cache.set("k1", "v1")
        cache.get("k1")  # Hit
        cache.get("k2")  # Miss
        assert cache.hit_rate == 0.5


class TestWriteThrough:
    def test_write_updates_both(self):
        cache = WriteThrough()
        db = {}
        cache.write("k1", "v1", lambda k, v: db.update({k: v}))
        assert cache.get("k1") == "v1"
        assert db["k1"] == "v1"


class TestCacheEntry:
    def test_not_expired(self):
        entry = CacheEntry(value="test", ttl=300.0)
        assert entry.is_expired is False

    def test_expired(self):
        import time
        entry = CacheEntry(value="test", ttl=0.0)
        time.sleep(0.01)  # Ensure time passes beyond ttl=0
        assert entry.is_expired is True
