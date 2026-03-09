"""
Materialized Views — Incremental Aggregation
===============================================

A materialized view (MV) is a pre-computed query result that is
stored and automatically updated when the source data changes.

CLICKHOUSE MVs:
- Triggered on INSERT to the source table (not UPDATE/DELETE).
- Only process the NEW data in each insert batch (incremental).
- Store results in a target table (often AggregatingMergeTree).
- Much more efficient than re-running the full query each time.

REFRESH STRATEGIES:
1. **ON_INSERT** — Update immediately when source data is inserted.
   Lowest latency, but adds overhead to every insert.
2. **PERIODIC** — Refresh on a schedule (e.g., every 5 minutes).
   Good balance of freshness and performance.
3. **MANUAL** — Only refresh when explicitly triggered.
   Used for expensive aggregations that don't need real-time freshness.

EXAMPLE:
    Source table: raw_rides (ride_id, zone, fare, ts)
    MV query: SELECT zone, count(*) as rides, sum(fare) as total_fare
              FROM raw_rides GROUP BY zone
    Target table: rides_by_zone (zone, rides, total_fare)

    When 100 new rides are inserted, the MV only processes those 100
    rows and merges the partial aggregates into the target table.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class RefreshStrategy(str, Enum):
    ON_INSERT = "on_insert"
    PERIODIC = "periodic"
    MANUAL = "manual"


@dataclass
class AggregationSpec:
    """Defines an aggregation to compute in a materialized view."""
    group_by: list[str]
    aggregations: dict[str, str]  # column -> function (sum, count, avg, min, max)


class MaterializedView:
    """
    Simulates a ClickHouse materialized view with incremental refresh.

    The MV watches a source table. When new data is inserted,
    it processes only the new rows and updates its internal state.

    KEY INSIGHT:
    Unlike a regular view (which re-runs the query each time),
    a materialized view stores the result and only processes deltas.
    This makes queries against the MV instant, regardless of source size.
    """

    def __init__(
        self,
        name: str,
        aggregation: AggregationSpec,
        strategy: RefreshStrategy = RefreshStrategy.ON_INSERT,
    ) -> None:
        self.name = name
        self.aggregation = aggregation
        self.strategy = strategy
        self._state: dict[tuple, dict[str, Any]] = {}
        self._rows_processed = 0
        self._refresh_count = 0

    @property
    def rows_processed(self) -> int:
        return self._rows_processed

    @property
    def refresh_count(self) -> int:
        return self._refresh_count

    def on_insert(self, new_rows: list[dict[str, Any]]) -> None:
        """
        Called when new data is inserted into the source table.

        If strategy is ON_INSERT, immediately processes the new rows.
        Otherwise, buffers them for later refresh.
        """
        if self.strategy == RefreshStrategy.ON_INSERT:
            self._process_rows(new_rows)

    def refresh(self, all_rows: list[dict[str, Any]]) -> None:
        """
        Full refresh — recompute from all source data.

        Used for PERIODIC and MANUAL strategies, or to correct drift.
        """
        self._state.clear()
        self._process_rows(all_rows)
        self._refresh_count += 1

    def _process_rows(self, rows: list[dict[str, Any]]) -> None:
        """Process a batch of rows — compute partial aggregates and merge."""
        for row in rows:
            group_key = tuple(
                row.get(col) for col in self.aggregation.group_by
            )

            if group_key not in self._state:
                self._state[group_key] = {
                    col: row.get(col)
                    for col in self.aggregation.group_by
                }
                self._state[group_key]["_count"] = 0
                for col in self.aggregation.aggregations:
                    self._state[group_key][col] = None

            state = self._state[group_key]
            state["_count"] += 1

            for col, func in self.aggregation.aggregations.items():
                val = row.get(col)
                if val is None:
                    continue
                current = state[col]
                if current is None:
                    state[col] = val if func != "count" else 1
                elif func == "sum":
                    state[col] += val
                elif func == "count":
                    state[col] += 1
                elif func == "min":
                    state[col] = min(state[col], val)
                elif func == "max":
                    state[col] = max(state[col], val)
                elif func == "avg":
                    # For avg, we store running sum and use _count
                    state[col] += val

            self._rows_processed += 1

    def query(self) -> list[dict[str, Any]]:
        """Query the materialized view results."""
        results = []
        for key, state in self._state.items():
            row = {}
            for col in self.aggregation.group_by:
                row[col] = state[col]
            for col, func in self.aggregation.aggregations.items():
                if func == "avg" and state["_count"] > 0 and state[col] is not None:
                    row[col] = round(state[col] / state["_count"], 4)
                else:
                    row[col] = state[col]
            row["_count"] = state["_count"]
            results.append(row)
        return sorted(
            results,
            key=lambda r: tuple(r.get(col) for col in self.aggregation.group_by),
        )

    def get_state_for_group(self, group_values: dict[str, Any]) -> dict[str, Any] | None:
        """Look up the aggregated state for a specific group."""
        key = tuple(group_values.get(col) for col in self.aggregation.group_by)
        if key in self._state:
            return dict(self._state[key])
        return None
