"""
Partition Key Selection & Pruning
====================================

Partitioning divides a table into smaller physical segments based
on a partition key expression. Each partition is stored separately,
enabling the query engine to skip entire partitions that can't
match the query.

KEY CONCEPTS:

1. **Partition Key** — An expression that determines which partition
   a row belongs to. Common choices:
   - toYYYYMM(timestamp) — Monthly partitions.
   - toDate(timestamp) — Daily partitions.
   - cityHash64(user_id) % 10 — Hash-based partitions.

2. **Partition Pruning** — When a query has a WHERE clause that
   constrains the partition key, the engine reads only the matching
   partitions. This can skip 99%+ of the data.

3. **Hot/Cold Storage** — Recent partitions (hot) on fast SSD,
   old partitions (cold) on cheaper HDD/S3. ClickHouse TTL rules
   can automate this.

4. **Partition Key Advisor** — Choosing the right partition key
   depends on query patterns and data distribution. Too many
   partitions = overhead. Too few = no pruning benefit.

CLICKHOUSE SPECIFICS:
- Partitions are defined in ENGINE = MergeTree PARTITION BY expr.
- Each partition is a set of "parts" on disk.
- ALTER TABLE ... DETACH/ATTACH PARTITION for data management.
- TTL ... TO DISK 'cold' for automatic cold storage movement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Any


@dataclass
class Partition:
    """A single partition containing a subset of table data."""
    partition_key: str
    rows: list[dict[str, Any]]
    created_at: str = ""
    storage_tier: str = "hot"  # "hot" or "cold"

    @property
    def row_count(self) -> int:
        return len(self.rows)


class PartitionedTable:
    """
    A table partitioned by a key expression.

    Data is distributed across partitions based on the partition key.
    Queries that filter on the partition key benefit from pruning.
    """

    def __init__(self, name: str, partition_key: str) -> None:
        self.name = name
        self.partition_key = partition_key
        self._partitions: dict[str, Partition] = {}

    @property
    def partitions(self) -> dict[str, Partition]:
        return dict(self._partitions)

    @property
    def partition_count(self) -> int:
        return len(self._partitions)

    @property
    def total_rows(self) -> int:
        return sum(p.row_count for p in self._partitions.values())

    def insert(self, rows: list[dict[str, Any]]) -> dict[str, int]:
        """
        Insert rows, routing each to the correct partition.

        Returns a count of rows per partition.
        """
        partition_counts: dict[str, int] = {}
        for row in rows:
            pk_value = self._compute_partition_key(row)
            if pk_value not in self._partitions:
                self._partitions[pk_value] = Partition(
                    partition_key=pk_value,
                    rows=[],
                    created_at=datetime.now().isoformat(),
                )
            self._partitions[pk_value].rows.append(dict(row))
            partition_counts[pk_value] = partition_counts.get(pk_value, 0) + 1
        return partition_counts

    def query(
        self, filters: dict[str, Any] | None = None
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        """
        Query with automatic partition pruning.

        If filters constrain the partition key, only matching
        partitions are scanned.
        """
        partitions_to_scan = self._prune_partitions(filters)
        total_partitions = len(self._partitions)
        scanned_partitions = len(partitions_to_scan)

        results = []
        for partition in partitions_to_scan:
            for row in partition.rows:
                if self._matches_filters(row, filters):
                    results.append(dict(row))

        stats = {
            "partitions_total": total_partitions,
            "partitions_scanned": scanned_partitions,
            "partitions_pruned": total_partitions - scanned_partitions,
            "rows_scanned": sum(p.row_count for p in partitions_to_scan),
            "rows_returned": len(results),
        }
        return results, stats

    def partition_prune(
        self, query_filters: dict[str, Any]
    ) -> list[str]:
        """
        Determine which partitions are needed for the given filters.

        Returns the list of partition keys that must be scanned.
        """
        pruned = self._prune_partitions(query_filters)
        return [p.partition_key for p in pruned]

    def _compute_partition_key(self, row: dict[str, Any]) -> str:
        """Compute the partition key value for a row."""
        value = row.get(self.partition_key, "")
        if isinstance(value, str) and len(value) >= 7:
            # Assume YYYY-MM format for date-like strings
            return value[:7]  # Monthly partitions
        return str(value)

    def _prune_partitions(
        self, filters: dict[str, Any] | None
    ) -> list[Partition]:
        """Return only partitions that might match the filters."""
        if not filters or self.partition_key not in filters:
            return list(self._partitions.values())

        filter_value = str(filters[self.partition_key])
        # Check if any partition key matches or contains the filter value
        matching = []
        for pk, partition in self._partitions.items():
            if filter_value.startswith(pk) or pk.startswith(filter_value[:7]):
                matching.append(partition)

        return matching if matching else list(self._partitions.values())

    def _matches_filters(
        self, row: dict[str, Any], filters: dict[str, Any] | None
    ) -> bool:
        """Check if a row matches all filters."""
        if not filters:
            return True
        for key, value in filters.items():
            row_val = row.get(key)
            if isinstance(value, tuple) and len(value) == 2:
                # Range filter (min, max)
                if row_val is None or not (value[0] <= row_val <= value[1]):
                    return False
            elif row_val != value:
                return False
        return True


class HotColdStorage:
    """
    Manages hot/cold tiered storage for partitions.

    Hot storage (SSD): Recent data, frequently queried.
    Cold storage (HDD/S3): Old data, infrequently queried.

    In ClickHouse:
        ALTER TABLE rides MODIFY TTL event_date + INTERVAL 90 DAY TO DISK 'cold';
    """

    def __init__(
        self,
        hot_threshold_days: int = 90,
        reference_date: str = "2024-06-01",
    ) -> None:
        self.hot_threshold_days = hot_threshold_days
        self.reference_date = reference_date

    def classify_partitions(
        self, table: PartitionedTable
    ) -> dict[str, list[str]]:
        """
        Classify partitions into hot and cold tiers.

        Returns {"hot": [...partition_keys], "cold": [...partition_keys]}.
        """
        hot: list[str] = []
        cold: list[str] = []

        for pk in table.partitions:
            if self._is_hot(pk):
                hot.append(pk)
            else:
                cold.append(pk)

        return {"hot": sorted(hot), "cold": sorted(cold)}

    def move_to_cold(self, table: PartitionedTable) -> list[str]:
        """Move cold partitions to cold storage tier."""
        moved = []
        for pk, partition in table.partitions.items():
            if not self._is_hot(pk) and partition.storage_tier == "hot":
                partition.storage_tier = "cold"
                moved.append(pk)
        return moved

    def _is_hot(self, partition_key: str) -> bool:
        """Check if a partition is in the hot tier."""
        try:
            # Simple comparison for YYYY-MM format
            return partition_key >= self.reference_date[:7]
        except (ValueError, TypeError):
            return True  # Default to hot if can't determine


class PartitionKeyAdvisor:
    """
    Recommends partition key based on query patterns and data distribution.

    Considerations:
    - Too many partitions (daily for 10 years = 3650) = metadata overhead.
    - Too few partitions (yearly) = minimal pruning benefit.
    - Partition key should align with the most common WHERE clause.
    """

    @staticmethod
    def recommend(
        query_patterns: list[dict[str, Any]],
        data_range_days: int,
        daily_rows: int,
    ) -> dict[str, Any]:
        """
        Recommend a partition strategy.

        Args:
            query_patterns: List of common query patterns with filters.
            data_range_days: Total number of days of data.
            daily_rows: Average rows inserted per day.

        Returns recommendation with partition key and rationale.
        """
        total_rows = data_range_days * daily_rows

        # Check what columns appear most in query filters
        filter_columns: dict[str, int] = {}
        for pattern in query_patterns:
            for col in pattern.get("filters", []):
                filter_columns[col] = filter_columns.get(col, 0) + 1

        most_filtered = max(filter_columns, key=filter_columns.get) if filter_columns else "date"

        # Determine granularity
        if data_range_days <= 90:
            granularity = "daily"
            partition_count = data_range_days
        elif data_range_days <= 730:
            granularity = "monthly"
            partition_count = data_range_days // 30
        else:
            granularity = "monthly"
            partition_count = data_range_days // 30

        # Warn if too many partitions
        warnings = []
        if partition_count > 1000:
            warnings.append(f"High partition count ({partition_count}). Consider coarser granularity.")
        if daily_rows < 1000:
            warnings.append("Low daily volume. Partitioning overhead may exceed benefits.")

        rows_per_partition = total_rows // max(partition_count, 1)

        return {
            "recommended_key": most_filtered,
            "granularity": granularity,
            "estimated_partitions": partition_count,
            "rows_per_partition": rows_per_partition,
            "warnings": warnings,
            "rationale": (
                f"Partition by '{most_filtered}' ({granularity}) because it appears "
                f"in {filter_columns.get(most_filtered, 0)}/{len(query_patterns)} queries. "
                f"This gives ~{partition_count} partitions with ~{rows_per_partition} rows each."
            ),
        }
