"""
MergeTree Engine Family (Simulated)
======================================

ClickHouse's MergeTree is the foundation of its storage engine.
Data is written in sorted "parts" that are periodically merged
in the background. Different MergeTree variants provide different
merge behaviors.

ENGINE VARIANTS:

1. **MergeTree** — The base engine. Append-only, sorted by primary key.
   Merging combines sorted parts for faster reads.

2. **ReplacingMergeTree** — Deduplicates rows by primary key during merge.
   Keeps the row with the highest version column. Until merge, duplicates
   exist — use FINAL keyword to get deduplicated results.

3. **SummingMergeTree** — Auto-sums numeric columns with the same primary
   key during merge. Useful for pre-aggregated counters.

4. **AggregatingMergeTree** — Stores intermediate aggregate states. Used
   with materialized views for incremental aggregation.

WHY MergeTree works:
- Write-optimized: Appends are fast (no random I/O).
- Read-optimized after merge: Data is sorted and compressed.
- Background merges happen asynchronously.
- Column-oriented storage means queries only read needed columns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import copy


class MergeTree:
    """
    Base MergeTree engine simulation.

    Data is stored in "parts" — each insert creates a new part.
    Parts are sorted by the primary key columns. A merge() operation
    combines parts into a single sorted structure.

    In real ClickHouse:
    - Each part is a directory on disk with column files.
    - Merges happen in the background automatically.
    - The primary key is a sparse index (every Nth row), not a unique constraint.
    """

    def __init__(self, primary_key: list[str]) -> None:
        self.primary_key = primary_key
        self._parts: list[list[dict[str, Any]]] = []

    @property
    def part_count(self) -> int:
        return len(self._parts)

    @property
    def total_rows(self) -> int:
        return sum(len(part) for part in self._parts)

    def insert(self, rows: list[dict[str, Any]]) -> None:
        """
        Insert rows as a new part. The part is sorted by primary key.

        In ClickHouse, each INSERT creates a new part on disk.
        Many small inserts = many small parts = slower reads until merge.
        Best practice: batch inserts (1000+ rows per INSERT).
        """
        if not rows:
            return
        sorted_rows = sorted(
            rows,
            key=lambda r: tuple(r.get(k) for k in self.primary_key),
        )
        self._parts.append([dict(r) for r in sorted_rows])

    def query(self, conditions: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """
        Query all parts, filtering by conditions.

        This scans all parts (no merge required). In ClickHouse,
        the sparse primary key index would skip irrelevant granules.
        """
        results = []
        for part in self._parts:
            for row in part:
                if conditions is None or all(
                    row.get(k) == v for k, v in conditions.items()
                ):
                    results.append(dict(row))
        return results

    def merge(self) -> None:
        """
        Merge all parts into a single sorted part.

        This is the core of MergeTree — combining multiple sorted
        sequences into one. In ClickHouse, this happens in the background.
        """
        if len(self._parts) <= 1:
            return

        all_rows = []
        for part in self._parts:
            all_rows.extend(part)

        all_rows.sort(key=lambda r: tuple(r.get(k) for k in self.primary_key))
        self._parts = [all_rows]


class ReplacingMergeTree(MergeTree):
    """
    MergeTree variant that deduplicates by primary key on merge.

    When multiple rows share the same primary key, only the one with
    the highest version_column value is kept after merge.

    USE CASE: Upserts. Insert a new version of a row, and after merge
    the old version disappears. Before merge, both versions exist.

    IMPORTANT: Until merge, duplicates are visible! Use FINAL to get
    deduplicated results without waiting for merge:
        SELECT * FROM table FINAL WHERE ...
    But FINAL is slower because it deduplicates at query time.
    """

    def __init__(self, primary_key: list[str], version_column: str = "version") -> None:
        super().__init__(primary_key)
        self.version_column = version_column

    def merge(self) -> None:
        """Merge and deduplicate: keep only the latest version per primary key."""
        if len(self._parts) <= 1 and len(self._parts[0]) if self._parts else 0:
            # Still merge single parts for dedup within a part
            pass

        all_rows = []
        for part in self._parts:
            all_rows.extend(part)

        # Group by primary key, keep highest version
        best: dict[tuple, dict[str, Any]] = {}
        for row in all_rows:
            pk = tuple(row.get(k) for k in self.primary_key)
            version = row.get(self.version_column, 0)
            if pk not in best or version > best[pk].get(self.version_column, 0):
                best[pk] = dict(row)

        merged = sorted(
            best.values(),
            key=lambda r: tuple(r.get(k) for k in self.primary_key),
        )
        self._parts = [merged] if merged else []

    def final_query(self, conditions: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """
        Query with FINAL semantics — deduplicate at query time.

        This is equivalent to SELECT * FROM table FINAL in ClickHouse.
        Slower than a normal query because it deduplicates on the fly.
        """
        all_rows = self.query(conditions)
        best: dict[tuple, dict[str, Any]] = {}
        for row in all_rows:
            pk = tuple(row.get(k) for k in self.primary_key)
            version = row.get(self.version_column, 0)
            if pk not in best or version > best[pk].get(self.version_column, 0):
                best[pk] = dict(row)
        return sorted(
            best.values(),
            key=lambda r: tuple(r.get(k) for k in self.primary_key),
        )


class SummingMergeTree(MergeTree):
    """
    MergeTree variant that auto-sums numeric columns on merge.

    Rows with the same primary key are collapsed into one, with
    specified numeric columns summed.

    USE CASE: Pre-aggregated counters. Insert incremental values,
    and merge collapses them into running totals.

    Example:
        INSERT (date='2024-01-01', zone='A', rides=5, fare=100)
        INSERT (date='2024-01-01', zone='A', rides=3, fare=60)
        After merge: (date='2024-01-01', zone='A', rides=8, fare=160)
    """

    def __init__(self, primary_key: list[str], sum_columns: list[str]) -> None:
        super().__init__(primary_key)
        self.sum_columns = sum_columns

    def merge(self) -> None:
        """Merge and sum numeric columns for rows with the same primary key."""
        all_rows = []
        for part in self._parts:
            all_rows.extend(part)

        sums: dict[tuple, dict[str, Any]] = {}
        for row in all_rows:
            pk = tuple(row.get(k) for k in self.primary_key)
            if pk not in sums:
                sums[pk] = dict(row)
            else:
                for col in self.sum_columns:
                    sums[pk][col] = sums[pk].get(col, 0) + row.get(col, 0)

        merged = sorted(
            sums.values(),
            key=lambda r: tuple(r.get(k) for k in self.primary_key),
        )
        self._parts = [merged] if merged else []


class AggregatingMergeTree:
    """
    MergeTree variant that stores intermediate aggregate states.

    Instead of raw rows, it stores partial aggregation results
    that can be merged. This enables two-phase aggregation:
    1. Partial aggregate on insert (map phase).
    2. Final merge of partial states (reduce phase).

    USE CASE: Materialized views that incrementally aggregate.
    Each batch of inserts produces partial aggregates. The merge
    combines them into the final result.
    """

    def __init__(self, primary_key: list[str], agg_columns: dict[str, str]) -> None:
        """
        Args:
            primary_key: Columns that form the group-by key.
            agg_columns: Mapping of column_name -> agg_function (sum, count, min, max).
        """
        self.primary_key = primary_key
        self.agg_columns = agg_columns
        self._states: dict[tuple, dict[str, Any]] = {}

    def insert_partial(self, rows: list[dict[str, Any]]) -> None:
        """
        Insert a batch of rows, computing partial aggregates per group.
        """
        for row in rows:
            pk = tuple(row.get(k) for k in self.primary_key)
            if pk not in self._states:
                self._states[pk] = {k: row.get(k) for k in self.primary_key}
                self._states[pk]["_count"] = 0
                for col in self.agg_columns:
                    self._states[pk][col] = None

            state = self._states[pk]
            state["_count"] = state.get("_count", 0) + 1

            for col, func in self.agg_columns.items():
                val = row.get(col)
                if val is None:
                    continue
                if state[col] is None:
                    state[col] = val
                elif func == "sum":
                    state[col] += val
                elif func == "count":
                    state[col] += 1
                elif func == "min":
                    state[col] = min(state[col], val)
                elif func == "max":
                    state[col] = max(state[col], val)

    def get_results(self) -> list[dict[str, Any]]:
        """Get final aggregated results."""
        return sorted(
            [dict(s) for s in self._states.values()],
            key=lambda r: tuple(r.get(k) for k in self.primary_key),
        )
