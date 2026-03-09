"""
Parquet Format Concepts (Simulated)
=====================================

Apache Parquet is a columnar storage format designed for analytics.
This module simulates Parquet concepts without actual Parquet files.

WHY PARQUET:
- **Columnar**: Queries that only need 3 of 50 columns read only those 3.
- **Compressed**: Similar values in a column compress well (run-length, dictionary).
- **Typed**: Strong schema enforcement prevents data corruption.
- **Splittable**: Big files can be processed in parallel (row groups).

KEY CONCEPTS SIMULATED:

1. **Schema** — Column definitions with types and nullable flags.
2. **Column Pruning** — Read only the columns you need.
3. **Predicate Pushdown** — Skip row groups that can't match the filter.
4. **Partitioning** — Organize files by partition columns (year/month/day).
5. **Schema Evolution** — Adding columns, widening types.

ROW GROUPS:
Parquet files are divided into row groups (typically 128MB each).
Each row group has column chunks with min/max statistics.
When a query filters on a column, row groups whose min/max
don't overlap the filter range are skipped entirely.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ColumnDef:
    """Definition of a single column in a Parquet schema."""
    name: str
    dtype: str  # "string", "int", "float", "bool", "timestamp"
    nullable: bool = True


class ParquetSchema:
    """
    Parquet file schema — defines columns, types, and constraints.

    In real Parquet, the schema is stored in the file footer along
    with row group statistics (min, max, null count per column).
    """

    def __init__(self, columns: list[ColumnDef]) -> None:
        self.columns = list(columns)
        self._column_map = {c.name: c for c in columns}

    @property
    def column_names(self) -> list[str]:
        return [c.name for c in self.columns]

    def get_column(self, name: str) -> ColumnDef | None:
        return self._column_map.get(name)

    def validate_record(self, record: dict[str, Any]) -> list[str]:
        """Validate a record against the schema. Returns list of errors."""
        errors = []
        for col in self.columns:
            value = record.get(col.name)
            if value is None and not col.nullable:
                errors.append(f"Column '{col.name}' is not nullable but got None")
            elif value is not None:
                if col.dtype == "int" and not isinstance(value, int):
                    errors.append(f"Column '{col.name}' expects int, got {type(value).__name__}")
                elif col.dtype == "float" and not isinstance(value, (int, float)):
                    errors.append(f"Column '{col.name}' expects float, got {type(value).__name__}")
                elif col.dtype == "bool" and not isinstance(value, bool):
                    errors.append(f"Column '{col.name}' expects bool, got {type(value).__name__}")
                elif col.dtype == "string" and not isinstance(value, str):
                    errors.append(f"Column '{col.name}' expects string, got {type(value).__name__}")
        return errors


@dataclass
class RowGroup:
    """A row group with column statistics for predicate pushdown."""
    rows: list[dict[str, Any]]
    stats: dict[str, dict[str, Any]] = field(default_factory=dict)

    def compute_stats(self, columns: list[str]) -> None:
        """Compute min/max/null_count statistics per column."""
        for col in columns:
            values = [r.get(col) for r in self.rows if r.get(col) is not None]
            null_count = sum(1 for r in self.rows if r.get(col) is None)
            self.stats[col] = {
                "min": min(values) if values else None,
                "max": max(values) if values else None,
                "null_count": null_count,
                "count": len(self.rows),
            }


class ParquetWriter:
    """
    Simulates writing records in Parquet format with schema enforcement.

    Features:
    - Schema validation on write.
    - Partitioning by specified columns.
    - Row group creation (batching rows).
    """

    def __init__(
        self,
        schema: ParquetSchema,
        row_group_size: int = 100,
        partition_columns: list[str] | None = None,
    ) -> None:
        self.schema = schema
        self.row_group_size = row_group_size
        self.partition_columns = partition_columns or []
        self._partitions: dict[tuple, list[RowGroup]] = {}
        self._current_buffer: list[dict[str, Any]] = []
        self._current_partition: tuple = ()
        self._total_written = 0

    @property
    def total_written(self) -> int:
        return self._total_written

    @property
    def partition_keys(self) -> list[tuple]:
        return list(self._partitions.keys())

    def write(self, records: list[dict[str, Any]]) -> int:
        """
        Write records with schema validation and partitioning.
        Returns number of records successfully written.
        """
        written = 0
        for record in records:
            errors = self.schema.validate_record(record)
            if errors:
                continue  # Skip invalid records

            # Determine partition
            part_key = tuple(
                record.get(col) for col in self.partition_columns
            ) if self.partition_columns else ()

            if part_key not in self._partitions:
                self._partitions[part_key] = []

            # Add to partition's latest row group or create new one
            if (
                not self._partitions[part_key]
                or len(self._partitions[part_key][-1].rows) >= self.row_group_size
            ):
                rg = RowGroup(rows=[])
                self._partitions[part_key].append(rg)

            self._partitions[part_key][-1].rows.append(dict(record))
            written += 1
            self._total_written += 1

        # Compute stats for all row groups
        for part_key, row_groups in self._partitions.items():
            for rg in row_groups:
                rg.compute_stats(self.schema.column_names)

        return written

    def get_row_groups(self, partition_key: tuple | None = None) -> list[RowGroup]:
        """Get row groups, optionally filtered by partition."""
        if partition_key is not None:
            return list(self._partitions.get(partition_key, []))
        all_groups = []
        for groups in self._partitions.values():
            all_groups.extend(groups)
        return all_groups


class ParquetReader:
    """
    Simulates reading Parquet with column pruning and predicate pushdown.

    Column pruning: Only read the columns you need.
    Predicate pushdown: Skip row groups whose stats don't match the filter.
    """

    def __init__(self, writer: ParquetWriter) -> None:
        self._writer = writer

    def read(
        self,
        columns: list[str] | None = None,
        predicates: dict[str, tuple[str, Any]] | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        """
        Read records with optional column pruning and predicate pushdown.

        Args:
            columns: Columns to include (None = all).
            predicates: Column -> (operator, value). Operators: eq, gt, lt, gte, lte.

        Returns:
            (results, stats) where stats includes row_groups_scanned,
            row_groups_skipped, rows_scanned.
        """
        all_columns = columns or self._writer.schema.column_names
        preds = predicates or {}

        total_groups = 0
        skipped_groups = 0
        results = []

        for rg in self._writer.get_row_groups():
            total_groups += 1

            # Predicate pushdown: check row group stats
            if self._can_skip_group(rg, preds):
                skipped_groups += 1
                continue

            # Scan rows in this row group
            for row in rg.rows:
                if self._matches_predicates(row, preds):
                    # Column pruning: only include requested columns
                    pruned = {col: row.get(col) for col in all_columns}
                    results.append(pruned)

        stats = {
            "row_groups_total": total_groups,
            "row_groups_scanned": total_groups - skipped_groups,
            "row_groups_skipped": skipped_groups,
            "rows_returned": len(results),
        }
        return results, stats

    def _can_skip_group(
        self, rg: RowGroup, predicates: dict[str, tuple[str, Any]]
    ) -> bool:
        """Check if a row group can be skipped based on min/max stats."""
        for col, (op, val) in predicates.items():
            if col not in rg.stats:
                continue
            col_stats = rg.stats[col]
            col_min = col_stats.get("min")
            col_max = col_stats.get("max")
            if col_min is None or col_max is None:
                continue

            # If the filter can't possibly match any row in this group, skip
            if op == "eq" and (val < col_min or val > col_max):
                return True
            if op == "gt" and col_max <= val:
                return True
            if op == "gte" and col_max < val:
                return True
            if op == "lt" and col_min >= val:
                return True
            if op == "lte" and col_min > val:
                return True
        return False

    def _matches_predicates(
        self, row: dict[str, Any], predicates: dict[str, tuple[str, Any]]
    ) -> bool:
        """Check if a row matches all predicates."""
        for col, (op, val) in predicates.items():
            row_val = row.get(col)
            if row_val is None:
                return False
            if op == "eq" and row_val != val:
                return False
            if op == "gt" and not (row_val > val):
                return False
            if op == "gte" and not (row_val >= val):
                return False
            if op == "lt" and not (row_val < val):
                return False
            if op == "lte" and not (row_val <= val):
                return False
        return True


class SchemaEvolution:
    """
    Handles schema evolution for Parquet files.

    Schema evolution allows adding new columns or widening types
    without rewriting existing data. This is critical for long-lived
    data lakes where the schema changes over time.

    Supported operations:
    - Add column (with default value for existing rows).
    - Widen type (e.g., int -> float).
    - Check backward compatibility.
    """

    # Type widening rules: type -> set of types it can be widened to
    WIDEN_RULES: dict[str, set[str]] = {
        "int": {"float", "string"},
        "float": {"string"},
        "bool": {"string", "int"},
        "string": set(),  # String is the widest type
    }

    @staticmethod
    def can_widen(from_type: str, to_type: str) -> bool:
        """Check if a type can be widened to another type."""
        if from_type == to_type:
            return True
        return to_type in SchemaEvolution.WIDEN_RULES.get(from_type, set())

    @staticmethod
    def add_column(
        schema: ParquetSchema, column: ColumnDef
    ) -> ParquetSchema:
        """Add a new column to an existing schema."""
        if column.name in schema.column_names:
            raise ValueError(f"Column '{column.name}' already exists")
        new_columns = list(schema.columns) + [column]
        return ParquetSchema(new_columns)

    @staticmethod
    def is_backward_compatible(
        old_schema: ParquetSchema, new_schema: ParquetSchema
    ) -> tuple[bool, list[str]]:
        """
        Check if the new schema is backward compatible with the old.

        Backward compatible means:
        - All old columns still exist.
        - Old column types haven't narrowed (only widened).
        - New columns must be nullable (old data won't have them).
        """
        issues: list[str] = []
        old_cols = {c.name: c for c in old_schema.columns}

        for old_col in old_schema.columns:
            new_col = new_schema.get_column(old_col.name)
            if new_col is None:
                issues.append(f"Column '{old_col.name}' was removed")
            elif old_col.dtype != new_col.dtype:
                if not SchemaEvolution.can_widen(old_col.dtype, new_col.dtype):
                    issues.append(
                        f"Column '{old_col.name}' type change from "
                        f"'{old_col.dtype}' to '{new_col.dtype}' is not a widening"
                    )

        # New columns must be nullable
        for new_col in new_schema.columns:
            if new_col.name not in old_cols and not new_col.nullable:
                issues.append(
                    f"New column '{new_col.name}' must be nullable for "
                    f"backward compatibility"
                )

        return (len(issues) == 0, issues)
