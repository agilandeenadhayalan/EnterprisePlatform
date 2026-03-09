"""
Exercise 6: Partition Pruning Optimizer
=========================================

The query optimization module demonstrated how partition pruning
skips irrelevant partitions. Now implement your own.

TASK:
Given a table partitioned by month (YYYY-MM), implement:
1. Route records to the correct monthly partition.
2. Given a date range query, determine which partitions are needed.
3. Calculate the savings (% of partitions skipped).

WHY partition pruning:
- Instead of scanning 12 months of data, only scan the 2 that match.
- Reduces I/O by 80%+ for range-filtered queries.
- Critical for large tables (billions of rows).
"""


class PartitionPruner:
    """
    TODO: Implement partition pruning for a monthly-partitioned table.

    The pruner should:
    1. Route records to monthly partitions (YYYY-MM)
    2. Given a date range, return only matching partitions
    3. Calculate savings (% partitions skipped)
    """

    def __init__(self) -> None:
        """
        Initialize the partition storage.

        Hint: Use a dict mapping partition key (e.g., "2024-01") to list of records.
        """
        # TODO: Initialize (~1 line)
        raise NotImplementedError("Initialize partitions")

    def _partition_key(self, date_str: str) -> str:
        """
        Extract the monthly partition key from a date string.

        Example: "2024-03-15" -> "2024-03"
        """
        # TODO: Implement (~1 line)
        raise NotImplementedError("Extract partition key")

    def insert(self, records: list[dict], date_column: str = "date") -> dict[str, int]:
        """
        Insert records into the correct partitions.

        Each record is routed to a partition based on its date column.
        Returns a dict mapping partition_key -> count of records inserted.
        """
        # TODO: Implement (~8 lines)
        raise NotImplementedError("Insert records")

    def prune(self, start_date: str, end_date: str) -> list[str]:
        """
        Given a date range [start_date, end_date], return the list
        of partition keys that could contain matching records.

        Example:
            start_date="2024-02-15", end_date="2024-04-10"
            -> ["2024-02", "2024-03", "2024-04"]

        Hint: Compare partition keys (YYYY-MM) with the range
        start_date[:7] through end_date[:7].
        """
        # TODO: Implement (~5 lines)
        raise NotImplementedError("Prune partitions")

    def query(
        self, start_date: str, end_date: str, date_column: str = "date"
    ) -> tuple[list[dict], dict[str, int]]:
        """
        Query records within the date range, using partition pruning.

        Returns:
        - List of matching records.
        - Stats dict with: partitions_total, partitions_scanned,
          partitions_pruned, savings_pct.
        """
        # TODO: Implement (~15 lines)
        raise NotImplementedError("Query with pruning")


# ── Verification ──


def test_partition_routing():
    pruner = PartitionPruner()
    counts = pruner.insert([
        {"id": 1, "date": "2024-01-15"},
        {"id": 2, "date": "2024-01-20"},
        {"id": 3, "date": "2024-02-10"},
    ])
    assert counts["2024-01"] == 2
    assert counts["2024-02"] == 1


def test_prune_returns_matching_partitions():
    pruner = PartitionPruner()
    pruner.insert([
        {"id": 1, "date": "2024-01-15"},
        {"id": 2, "date": "2024-02-10"},
        {"id": 3, "date": "2024-03-05"},
        {"id": 4, "date": "2024-04-20"},
        {"id": 5, "date": "2024-05-01"},
    ])
    needed = pruner.prune("2024-02-01", "2024-03-31")
    assert "2024-02" in needed
    assert "2024-03" in needed
    assert "2024-01" not in needed
    assert "2024-04" not in needed


def test_query_with_savings():
    pruner = PartitionPruner()
    for month in range(1, 13):
        pruner.insert([{"id": month, "date": f"2024-{month:02d}-15", "fare": 10 * month}])
    results, stats = pruner.query("2024-03-01", "2024-04-30")
    assert stats["partitions_scanned"] == 2
    assert stats["partitions_pruned"] == 10
    # Savings should be ~83% (10/12 * 100)
    assert stats["savings_pct"] > 80


def test_empty_range():
    pruner = PartitionPruner()
    pruner.insert([{"id": 1, "date": "2024-06-15"}])
    needed = pruner.prune("2024-01-01", "2024-02-28")
    assert len(needed) == 0


if __name__ == "__main__":
    try:
        test_partition_routing()
        test_prune_returns_matching_partitions()
        test_query_with_savings()
        test_empty_range()
        print("All tests passed!")
    except NotImplementedError as e:
        print(f"Not yet implemented: {e}")
    except AssertionError as e:
        print(f"Test failed: {e}")
