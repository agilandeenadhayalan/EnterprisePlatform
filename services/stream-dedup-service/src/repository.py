"""
Stream Dedup Service repository — sliding window deduplication with in-memory sets.
"""

import time
from collections import OrderedDict
from typing import Optional


class DedupRepository:
    """
    In-memory sliding window deduplication.
    Uses an OrderedDict to maintain insertion order for expiry.
    """

    def __init__(self, window_seconds: int = 3600, max_cache_size: int = 100000):
        self.window_seconds = window_seconds
        self.max_cache_size = max_cache_size
        self._seen: OrderedDict[str, float] = OrderedDict()  # event_id -> timestamp

        # Stats
        self.total_checked = 0
        self.total_unique = 0
        self.total_duplicates = 0
        self._start_time = time.time()

    def _evict_expired(self):
        """Remove expired entries from the sliding window."""
        cutoff = time.time() - self.window_seconds
        while self._seen:
            key, ts = next(iter(self._seen.items()))
            if ts < cutoff:
                self._seen.pop(key)
            else:
                break

    def _evict_if_full(self):
        """Evict oldest entries if cache exceeds max size."""
        while len(self._seen) > self.max_cache_size:
            self._seen.popitem(last=False)

    def check_and_dedup(
        self, events: list[dict], event_id_field: str = "event_id"
    ) -> tuple[list[dict], list[str]]:
        """
        Check a batch of events for duplicates.
        Returns (unique_events, duplicate_event_ids).
        """
        self._evict_expired()

        unique_events: list[dict] = []
        duplicate_ids: list[str] = []
        now = time.time()

        for event in events:
            event_id = event.get(event_id_field)
            self.total_checked += 1

            if event_id is None:
                # Events without an ID are treated as unique
                unique_events.append(event)
                self.total_unique += 1
                continue

            event_id_str = str(event_id)

            if event_id_str in self._seen:
                # Duplicate found
                duplicate_ids.append(event_id_str)
                self.total_duplicates += 1
            else:
                # New unique event
                self._seen[event_id_str] = now
                unique_events.append(event)
                self.total_unique += 1

        self._evict_if_full()
        return unique_events, duplicate_ids

    def get_cache_size(self) -> int:
        """Return current number of event IDs in the cache."""
        return len(self._seen)

    def clear_cache(self) -> int:
        """Clear the dedup cache. Returns number of cleared entries."""
        count = len(self._seen)
        self._seen.clear()
        return count

    def get_stats(self) -> dict:
        """Return deduplication statistics."""
        hit_rate = 0.0
        miss_rate = 0.0
        if self.total_checked > 0:
            hit_rate = round(self.total_duplicates / self.total_checked, 4)
            miss_rate = round(self.total_unique / self.total_checked, 4)

        return {
            "total_checked": self.total_checked,
            "total_unique": self.total_unique,
            "total_duplicates": self.total_duplicates,
            "hit_rate": hit_rate,
            "miss_rate": miss_rate,
            "cache_size": len(self._seen),
            "window_seconds": self.window_seconds,
            "max_cache_size": self.max_cache_size,
            "uptime_seconds": round(time.time() - self._start_time, 2),
        }

    def reset(self):
        """Reset all state."""
        self._seen.clear()
        self.total_checked = 0
        self.total_unique = 0
        self.total_duplicates = 0
        self._start_time = time.time()
