"""
ClickHouse Secondary Indexes (Skip Indexes)
==============================================

ClickHouse's primary index is sparse — it indexes every Nth row (granule),
not every row. This is fast for primary key queries but doesn't help
when filtering on non-primary-key columns.

Skip indexes (secondary indexes) add column-level metadata to each
granule, allowing the engine to SKIP entire granules that can't
match the query predicate.

INDEX TYPES:

1. **MinMax Index** — Stores the min and max value per granule.
   Skips granules where the range [min, max] doesn't overlap the filter.
   Best for: columns with locality (timestamps, sequential IDs).

2. **Set Index** — Stores all unique values per granule (up to max_size).
   Skips granules where the value is not in the set.
   Best for: low-cardinality columns (status, zone, vehicle_type).

3. **Bloom Filter Index** — Probabilistic membership test.
   Can have false positives but NEVER false negatives.
   Best for: high-cardinality columns (user_id, email) where exact
   membership testing would use too much memory.

GRANULARITY:
Each index entry covers N granules. Lower granularity = more index entries
= more precise skipping but more memory and CPU for index checks.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Granule:
    """A block of rows with associated index metadata."""
    granule_id: int
    rows: list[dict[str, Any]]


class MinMaxIndex:
    """
    MinMax skip index: stores min/max per granule.

    When a query filters on this column, granules where
    [min, max] doesn't overlap the filter range are skipped.

    Example:
        Granule 0: min=1, max=100
        Granule 1: min=101, max=200
        Query: WHERE id > 150
        -> Skip granule 0 entirely (max=100 < 150)
    """

    def __init__(self, column: str) -> None:
        self.column = column
        self._index: dict[int, tuple[Any, Any]] = {}  # granule_id -> (min, max)

    def build(self, granules: list[Granule]) -> None:
        """Build the index from a list of granules."""
        for granule in granules:
            values = [
                r[self.column] for r in granule.rows
                if self.column in r and r[self.column] is not None
            ]
            if values:
                self._index[granule.granule_id] = (min(values), max(values))

    def can_skip(self, granule_id: int, op: str, value: Any) -> bool:
        """
        Check if a granule can be skipped for the given predicate.

        Returns True if the granule CANNOT contain matching rows.
        """
        if granule_id not in self._index:
            return False

        g_min, g_max = self._index[granule_id]

        if op == "eq":
            return value < g_min or value > g_max
        elif op == "gt":
            return g_max <= value
        elif op == "gte":
            return g_max < value
        elif op == "lt":
            return g_min >= value
        elif op == "lte":
            return g_min > value
        elif op == "between":
            low, high = value
            return g_max < low or g_min > high
        return False

    def query(
        self, granules: list[Granule], op: str, value: Any
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        """Query with MinMax index skipping."""
        results = []
        skipped = 0
        scanned = 0

        for granule in granules:
            if self.can_skip(granule.granule_id, op, value):
                skipped += 1
                continue
            scanned += 1
            for row in granule.rows:
                if self._matches(row, op, value):
                    results.append(row)

        return results, {"granules_total": len(granules), "scanned": scanned, "skipped": skipped}

    def _matches(self, row: dict[str, Any], op: str, value: Any) -> bool:
        """Check if a row matches the predicate."""
        row_val = row.get(self.column)
        if row_val is None:
            return False
        if op == "eq":
            return row_val == value
        elif op == "gt":
            return row_val > value
        elif op == "gte":
            return row_val >= value
        elif op == "lt":
            return row_val < value
        elif op == "lte":
            return row_val <= value
        elif op == "between":
            low, high = value
            return low <= row_val <= high
        return False


class SetIndex:
    """
    Set skip index: stores unique values per granule.

    Skips granules where the queried value is NOT in the set.
    If the set exceeds max_size, it becomes a full set (never skips).

    Best for low-cardinality columns like status or zone.
    """

    def __init__(self, column: str, max_size: int = 100) -> None:
        self.column = column
        self.max_size = max_size
        self._index: dict[int, set[Any] | None] = {}

    def build(self, granules: list[Granule]) -> None:
        """Build the set index."""
        for granule in granules:
            values = set(
                r[self.column] for r in granule.rows
                if self.column in r and r[self.column] is not None
            )
            if len(values) <= self.max_size:
                self._index[granule.granule_id] = values
            else:
                self._index[granule.granule_id] = None  # Too many values

    def can_skip(self, granule_id: int, value: Any) -> bool:
        """Check if a granule can be skipped (value not in its set)."""
        if granule_id not in self._index:
            return False
        value_set = self._index[granule_id]
        if value_set is None:
            return False  # Set overflowed, can't skip
        return value not in value_set

    def query(
        self, granules: list[Granule], value: Any
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        """Query with set index skipping."""
        results = []
        skipped = 0
        scanned = 0

        for granule in granules:
            if self.can_skip(granule.granule_id, value):
                skipped += 1
                continue
            scanned += 1
            for row in granule.rows:
                if row.get(self.column) == value:
                    results.append(row)

        return results, {"granules_total": len(granules), "scanned": scanned, "skipped": skipped}


class BloomFilterIndex:
    """
    Bloom filter skip index: probabilistic membership test.

    A Bloom filter uses multiple hash functions to map values into
    a bit array. It can:
    - Definitely say "NOT in the set" (no false negatives).
    - Say "MIGHT be in the set" (possible false positives).

    The false positive rate depends on the filter size and number
    of hash functions. Lower FP rate = more memory.

    Best for high-cardinality columns where an exact set would be
    too large (e.g., user_id, session_id).
    """

    def __init__(
        self,
        column: str,
        expected_elements: int = 1000,
        false_positive_rate: float = 0.01,
    ) -> None:
        self.column = column
        self.expected_elements = expected_elements
        self.false_positive_rate = false_positive_rate
        self._filters: dict[int, _BloomFilter] = {}

    def build(self, granules: list[Granule]) -> None:
        """Build Bloom filters for each granule."""
        for granule in granules:
            values = [
                r[self.column] for r in granule.rows
                if self.column in r and r[self.column] is not None
            ]
            bf = _BloomFilter(
                expected_elements=max(len(values), 1),
                fp_rate=self.false_positive_rate,
            )
            for v in values:
                bf.add(v)
            self._filters[granule.granule_id] = bf

    def can_skip(self, granule_id: int, value: Any) -> bool:
        """Check if a granule can be skipped (value not in Bloom filter)."""
        if granule_id not in self._filters:
            return False
        return not self._filters[granule_id].might_contain(value)

    def query(
        self, granules: list[Granule], value: Any
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        """Query with Bloom filter index skipping."""
        results = []
        skipped = 0
        scanned = 0

        for granule in granules:
            if self.can_skip(granule.granule_id, value):
                skipped += 1
                continue
            scanned += 1
            for row in granule.rows:
                if row.get(self.column) == value:
                    results.append(row)

        return results, {"granules_total": len(granules), "scanned": scanned, "skipped": skipped}


class _BloomFilter:
    """Simple Bloom filter implementation for educational purposes."""

    def __init__(self, expected_elements: int, fp_rate: float = 0.01) -> None:
        self._size = self._optimal_size(expected_elements, fp_rate)
        self._num_hashes = self._optimal_hashes(self._size, expected_elements)
        self._bits = [False] * self._size

    @staticmethod
    def _optimal_size(n: int, p: float) -> int:
        """Calculate optimal bit array size."""
        if n <= 0 or p <= 0 or p >= 1:
            return 64
        m = -(n * math.log(p)) / (math.log(2) ** 2)
        return max(int(m), 64)

    @staticmethod
    def _optimal_hashes(m: int, n: int) -> int:
        """Calculate optimal number of hash functions."""
        if n <= 0:
            return 1
        k = (m / n) * math.log(2)
        return max(int(k), 1)

    def _hashes(self, value: Any) -> list[int]:
        """Generate hash values for an element."""
        positions = []
        for i in range(self._num_hashes):
            h = hashlib.md5(f"{value}:{i}".encode()).hexdigest()
            positions.append(int(h, 16) % self._size)
        return positions

    def add(self, value: Any) -> None:
        """Add a value to the filter."""
        for pos in self._hashes(value):
            self._bits[pos] = True

    def might_contain(self, value: Any) -> bool:
        """Check if a value might be in the filter (may have false positives)."""
        return all(self._bits[pos] for pos in self._hashes(value))


class IndexSelector:
    """
    Recommends the best index type based on column characteristics.

    Selection criteria:
    - Low cardinality (<100 unique values) -> Set Index
    - High locality (sequential, time-based) -> MinMax Index
    - High cardinality (>1000 unique values) -> Bloom Filter
    - Moderate cardinality -> MinMax or Set depending on query pattern
    """

    @staticmethod
    def recommend(
        cardinality: int,
        total_rows: int,
        is_sequential: bool = False,
        query_pattern: str = "equality",
    ) -> str:
        """
        Recommend an index type.

        Args:
            cardinality: Number of distinct values.
            total_rows: Total rows in the table.
            is_sequential: Whether values are sequential (timestamps, IDs).
            query_pattern: "equality", "range", or "membership".
        """
        ratio = cardinality / total_rows if total_rows > 0 else 0

        if is_sequential or query_pattern == "range":
            return "minmax"
        elif ratio < 0.01 or cardinality < 100:
            return "set"
        elif cardinality > 1000 or query_pattern == "membership":
            return "bloom_filter"
        else:
            return "minmax"
