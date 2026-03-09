"""
Inference Cache (Prediction Cache)
====================================

Many inference requests have identical or very similar input features:
- Same pickup zone at the same hour = same surge prediction
- Same driver profile features = same ETA estimate

Computing a model prediction is expensive (especially on GPU). Caching
predictions for identical inputs can save significant compute:

    Cache hit rate of 30% at 10,000 QPS = 3,000 fewer inferences/second

This module implements an LRU (Least Recently Used) cache with TTL
(Time-To-Live) expiration:

**LRU**: When the cache is full, the least recently accessed entry is
evicted. This keeps frequently-requested predictions warm.

**TTL**: Even if an entry is frequently accessed, it's evicted after
ttl_seconds. This ensures predictions don't become stale -- the real
world changes, and old predictions may no longer be accurate.

The cache key is computed by hashing the model name + sorted feature
dict, ensuring that identical inputs always produce the same key.
"""

from __future__ import annotations

import hashlib
import json
from collections import OrderedDict


class PredictionCache:
    """LRU cache with TTL for deterministic ML predictions.

    Thread safety note: This implementation is NOT thread-safe.
    In production, you'd wrap operations with a lock or use a
    thread-safe data structure.
    """

    def __init__(
        self,
        max_size: int = 1000,
        ttl_seconds: float = 300.0,
    ) -> None:
        """Initialize the prediction cache.

        Args:
            max_size: Maximum number of cached predictions.
            ttl_seconds: Time-to-live for each cache entry in seconds.
        """
        if max_size < 1:
            raise ValueError("max_size must be >= 1")
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")

        self.max_size = max_size
        self.ttl_seconds = ttl_seconds

        # OrderedDict maintains insertion order; we move accessed items
        # to the end to implement LRU (least recently used = front).
        self._cache: OrderedDict[str, dict] = OrderedDict()

        # Statistics
        self._hits: int = 0
        self._misses: int = 0
        self._evictions: int = 0
        self._current_time: float = 0.0

    def get(self, cache_key: str, current_time: float | None = None) -> dict | None:
        """Look up a cached prediction.

        Args:
            cache_key: The cache key (from make_key()).
            current_time: Current unix timestamp. If None, uses the last
                         time seen. In production, pass time.time().

        Returns:
            The cached prediction dict, or None if not found / expired.
        """
        if current_time is not None:
            self._current_time = current_time

        if cache_key not in self._cache:
            self._misses += 1
            return None

        entry = self._cache[cache_key]

        # Check TTL expiration
        age = self._current_time - entry["cached_at"]
        if age > self.ttl_seconds:
            # Expired -- remove and count as miss
            del self._cache[cache_key]
            self._misses += 1
            return None

        # Cache hit -- move to end (most recently used)
        self._cache.move_to_end(cache_key)
        self._hits += 1
        return entry["prediction"]

    def put(
        self,
        cache_key: str,
        prediction: dict,
        current_time: float | None = None,
    ) -> None:
        """Store a prediction in the cache.

        Args:
            cache_key: The cache key (from make_key()).
            prediction: The prediction dict to cache.
            current_time: When this prediction was made.
        """
        if current_time is not None:
            self._current_time = current_time

        # If key already exists, update it
        if cache_key in self._cache:
            self._cache.move_to_end(cache_key)
            self._cache[cache_key] = {
                "prediction": prediction,
                "cached_at": self._current_time,
            }
            return

        # Evict LRU entry if cache is full
        if len(self._cache) >= self.max_size:
            self._cache.popitem(last=False)  # Remove oldest (LRU)
            self._evictions += 1

        self._cache[cache_key] = {
            "prediction": prediction,
            "cached_at": self._current_time,
        }

    def make_key(self, model_name: str, features: dict) -> str:
        """Create a deterministic cache key from model name and features.

        The key is a hash of the model name + sorted feature dict,
        ensuring identical inputs always produce the same key regardless
        of dict ordering.

        Args:
            model_name: The model being queried.
            features: Input features dict.

        Returns:
            A hex string cache key.
        """
        # Sort features for deterministic serialization
        key_parts = {
            "model": model_name,
            "features": dict(sorted(features.items())),
        }
        key_string = json.dumps(key_parts, sort_keys=True, default=str)
        return hashlib.sha256(key_string.encode()).hexdigest()[:16]

    def stats(self) -> dict:
        """Return cache statistics.

        Returns:
            Dict with hits, misses, hit_rate, size, evictions.
        """
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / total if total > 0 else 0.0,
            "size": len(self._cache),
            "evictions": self._evictions,
        }

    def clear(self) -> None:
        """Remove all entries from the cache."""
        self._cache.clear()
