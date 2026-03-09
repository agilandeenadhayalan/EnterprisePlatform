"""
Lakehouse — Combining Data Lake + Data Warehouse
===================================================

A lakehouse provides warehouse-like features (ACID transactions,
schema enforcement, time travel) on top of data lake storage.

KEY CONCEPTS:

1. **Table Format** — An abstraction layer over Parquet files that adds:
   - ACID transactions (atomic multi-file updates).
   - Snapshot isolation (readers and writers don't block each other).
   - Schema enforcement and evolution.
   - File-level metadata for efficient queries.

2. **Time Travel** — Query data as it existed at any past point in time.
   Enabled by maintaining a log of snapshots, each pointing to a set
   of data files. Rolling back = pointing to an older snapshot.

3. **Unified Query** — Query across Bronze/Silver/Gold layers
   using a single interface, similar to how a warehouse presents
   tables to SQL users.

REAL IMPLEMENTATIONS:
- Delta Lake (Databricks) — Transaction log in JSON/Parquet.
- Apache Iceberg (Netflix) — Manifest files with snapshot metadata.
- Apache Hudi (Uber) — Record-level upsert with timeline metadata.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Snapshot:
    """
    A point-in-time snapshot of a table's state.

    Each snapshot records which data files are active and
    schema information. This enables time travel.
    """
    snapshot_id: int
    timestamp: str
    records: list[dict[str, Any]]
    schema_version: int
    operation: str  # "append", "overwrite", "delete", "merge"
    records_added: int = 0
    records_removed: int = 0


class TableFormat:
    """
    Simulates Delta Lake / Iceberg table format.

    Provides:
    - ACID transactions via snapshot isolation.
    - Schema enforcement on write.
    - Schema evolution (add columns).
    - Time travel via snapshot history.

    In real Delta Lake:
    - A _delta_log/ directory stores JSON transaction log entries.
    - Each entry records file additions/removals.
    - Readers use the latest snapshot; writers create new entries.
    - Checkpoints compact the log periodically.
    """

    def __init__(self, name: str, schema: list[str] | None = None) -> None:
        self.name = name
        self.schema = schema or []
        self._schema_version = 1
        self._snapshots: list[Snapshot] = []
        self._current_records: list[dict[str, Any]] = []
        self._next_snapshot_id = 0

    @property
    def current_version(self) -> int:
        return len(self._snapshots)

    @property
    def snapshots(self) -> list[Snapshot]:
        return list(self._snapshots)

    @property
    def current_records(self) -> list[dict[str, Any]]:
        return [dict(r) for r in self._current_records]

    def append(self, records: list[dict[str, Any]]) -> Snapshot:
        """
        Append records to the table (creates a new snapshot).

        In Delta Lake, this creates new Parquet files and
        adds a transaction log entry referencing them.
        """
        new_records = [dict(r) for r in records]
        self._current_records.extend(new_records)
        return self._create_snapshot("append", records_added=len(new_records))

    def overwrite(self, records: list[dict[str, Any]]) -> Snapshot:
        """
        Overwrite the entire table with new records.

        In Delta Lake, this marks all existing files as removed
        and adds new files in a single transaction.
        """
        removed = len(self._current_records)
        self._current_records = [dict(r) for r in records]
        return self._create_snapshot(
            "overwrite", records_added=len(records), records_removed=removed
        )

    def delete(self, predicate: dict[str, Any]) -> Snapshot:
        """
        Delete records matching the predicate.

        In Delta Lake, this rewrites the affected files without
        the deleted records and updates the transaction log.
        """
        before = len(self._current_records)
        self._current_records = [
            r for r in self._current_records
            if not all(r.get(k) == v for k, v in predicate.items())
        ]
        removed = before - len(self._current_records)
        return self._create_snapshot("delete", records_removed=removed)

    def merge(
        self,
        source_records: list[dict[str, Any]],
        match_key: str,
    ) -> Snapshot:
        """
        Upsert: update matching records, insert new ones.

        In Delta Lake, MERGE handles complex conditional logic
        (WHEN MATCHED UPDATE, WHEN NOT MATCHED INSERT).
        """
        existing_keys = {r[match_key]: i for i, r in enumerate(self._current_records)}
        added = 0
        updated = 0

        for src in source_records:
            key = src[match_key]
            if key in existing_keys:
                idx = existing_keys[key]
                self._current_records[idx] = dict(src)
                updated += 1
            else:
                self._current_records.append(dict(src))
                added += 1

        return self._create_snapshot("merge", records_added=added)

    def add_column(self, column_name: str) -> None:
        """Add a column to the schema (schema evolution)."""
        if column_name not in self.schema:
            self.schema.append(column_name)
            self._schema_version += 1

    def _create_snapshot(
        self, operation: str, records_added: int = 0, records_removed: int = 0
    ) -> Snapshot:
        """Create a new snapshot with the current state."""
        self._next_snapshot_id += 1
        snapshot = Snapshot(
            snapshot_id=self._next_snapshot_id,
            timestamp=datetime.now().isoformat(),
            records=[dict(r) for r in self._current_records],
            schema_version=self._schema_version,
            operation=operation,
            records_added=records_added,
            records_removed=records_removed,
        )
        self._snapshots.append(snapshot)
        return snapshot


class TimeTravel:
    """
    Query a table as it existed at a specific point in time.

    Time travel enables:
    - Auditing: "What did the data look like last Tuesday?"
    - Debugging: "What changed between version 5 and version 10?"
    - Recovery: "Roll back to before that bad pipeline ran."

    In Delta Lake:
        SELECT * FROM table TIMESTAMP AS OF '2024-01-01'
        SELECT * FROM table VERSION AS OF 42
    """

    def __init__(self, table: TableFormat) -> None:
        self._table = table

    def as_of_version(self, version: int) -> list[dict[str, Any]]:
        """Query data as it existed at a specific snapshot version."""
        if version < 1 or version > len(self._table.snapshots):
            raise ValueError(
                f"Version {version} not found. Available: 1-{len(self._table.snapshots)}"
            )
        snapshot = self._table.snapshots[version - 1]
        return [dict(r) for r in snapshot.records]

    def as_of_timestamp(self, timestamp: str) -> list[dict[str, Any]]:
        """Query data as it existed at or before a specific timestamp."""
        matching = None
        for snapshot in self._table.snapshots:
            if snapshot.timestamp <= timestamp:
                matching = snapshot
            else:
                break

        if matching is None:
            raise ValueError(f"No snapshot found at or before {timestamp}")
        return [dict(r) for r in matching.records]

    def diff(
        self, version_old: int, version_new: int
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Compute the difference between two versions.

        Returns added, removed, and unchanged records.
        """
        old_records = self.as_of_version(version_old)
        new_records = self.as_of_version(version_new)

        old_set = {str(sorted(r.items())) for r in old_records}
        new_set = {str(sorted(r.items())) for r in new_records}

        added = [r for r in new_records if str(sorted(r.items())) not in old_set]
        removed = [r for r in old_records if str(sorted(r.items())) not in new_set]

        return {"added": added, "removed": removed}

    @property
    def history(self) -> list[dict[str, Any]]:
        """Get the history of all table operations."""
        return [
            {
                "version": s.snapshot_id,
                "timestamp": s.timestamp,
                "operation": s.operation,
                "records_added": s.records_added,
                "records_removed": s.records_removed,
                "total_records": len(s.records),
            }
            for s in self._table.snapshots
        ]


class Lakehouse:
    """
    Unified query interface over Bronze/Silver/Gold layers.

    Wraps multiple TableFormat instances representing different
    layers and provides a single query interface.
    """

    def __init__(self) -> None:
        self._tables: dict[str, TableFormat] = {}

    def register_table(self, layer: str, table: TableFormat) -> None:
        """Register a table under a layer name."""
        self._tables[layer] = table

    def query(
        self, layer: str, filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Query a specific layer with optional filters."""
        if layer not in self._tables:
            raise KeyError(f"Layer '{layer}' not registered")

        records = self._tables[layer].current_records
        if not filters:
            return records

        return [
            r for r in records
            if all(r.get(k) == v for k, v in filters.items())
        ]

    def layers(self) -> list[str]:
        """List all registered layers."""
        return list(self._tables.keys())

    def table(self, layer: str) -> TableFormat:
        """Get the TableFormat instance for a layer."""
        if layer not in self._tables:
            raise KeyError(f"Layer '{layer}' not registered")
        return self._tables[layer]
