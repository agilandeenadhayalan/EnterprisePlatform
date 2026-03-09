"""
Change Data Capture (CDC) Simulation
=======================================

CDC captures row-level changes (INSERT, UPDATE, DELETE) from a source
database and streams them to a target system.

CDC METHODS:

1. **Log-Based CDC** — Reads the database transaction log (WAL/binlog).
   - Most efficient: no impact on source queries.
   - Captures ALL changes including deletes.
   - Used by: Debezium, Maxwell, AWS DMS.

2. **Query-Based CDC** — Polls the source using an updated_at timestamp.
   - Simpler to implement but misses deletes.
   - Puts load on the source database.
   - Only captures rows that have an updated_at column.

3. **Trigger-Based CDC** — Database triggers write changes to a shadow table.
   - Captures all changes but adds overhead to every write.
   - Used in legacy systems.

CDC CHANGE FORMAT:
    {
        "op": "INSERT" | "UPDATE" | "DELETE",
        "before": { old values },  # null for INSERT
        "after": { new values },   # null for DELETE
        "timestamp": "...",
        "source": "table_name"
    }

CDC is critical for real-time data pipelines because it provides
a continuous stream of changes rather than periodic bulk extractions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import copy


class CDCOperation(str, Enum):
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


@dataclass(frozen=True)
class CDCEvent:
    """A single CDC change event."""
    operation: CDCOperation
    table: str
    key: str
    before: dict[str, Any] | None  # old values (null for INSERT)
    after: dict[str, Any] | None   # new values (null for DELETE)
    timestamp: str
    sequence: int


class CDCLog:
    """
    Append-only change log that records all row-level changes.

    In real databases, this is the Write-Ahead Log (PostgreSQL),
    Binary Log (MySQL), or Transaction Log (SQL Server).
    """

    def __init__(self) -> None:
        self._events: list[CDCEvent] = []
        self._sequence = 0

    @property
    def events(self) -> list[CDCEvent]:
        return list(self._events)

    @property
    def size(self) -> int:
        return len(self._events)

    def record_insert(self, table: str, key: str, values: dict[str, Any]) -> CDCEvent:
        """Record an INSERT operation."""
        return self._append(CDCOperation.INSERT, table, key, before=None, after=values)

    def record_update(
        self, table: str, key: str, before: dict[str, Any], after: dict[str, Any]
    ) -> CDCEvent:
        """Record an UPDATE operation."""
        return self._append(CDCOperation.UPDATE, table, key, before=before, after=after)

    def record_delete(self, table: str, key: str, values: dict[str, Any]) -> CDCEvent:
        """Record a DELETE operation."""
        return self._append(CDCOperation.DELETE, table, key, before=values, after=None)

    def get_events_since(self, sequence: int) -> list[CDCEvent]:
        """Get all events with sequence > the given value."""
        return [e for e in self._events if e.sequence > sequence]

    def _append(
        self,
        operation: CDCOperation,
        table: str,
        key: str,
        before: dict[str, Any] | None,
        after: dict[str, Any] | None,
    ) -> CDCEvent:
        self._sequence += 1
        event = CDCEvent(
            operation=operation,
            table=table,
            key=key,
            before=copy.deepcopy(before),
            after=copy.deepcopy(after),
            timestamp=datetime.now().isoformat(),
            sequence=self._sequence,
        )
        self._events.append(event)
        return event


class LogBasedCDC:
    """
    Log-based CDC: reads from the transaction log to capture changes.

    Advantages:
    - No impact on source database performance.
    - Captures all changes (INSERT, UPDATE, DELETE).
    - Preserves the exact order of changes.
    - Can capture schema changes too.

    In production, Debezium reads MySQL binlog or PostgreSQL WAL
    and publishes CDC events to Kafka topics.
    """

    def __init__(self, cdc_log: CDCLog) -> None:
        self._log = cdc_log
        self._last_sequence = 0

    @property
    def last_sequence(self) -> int:
        return self._last_sequence

    def poll(self) -> list[CDCEvent]:
        """
        Poll for new changes since the last read position.

        Returns new events and advances the read position.
        """
        events = self._log.get_events_since(self._last_sequence)
        if events:
            self._last_sequence = events[-1].sequence
        return events

    def peek(self) -> list[CDCEvent]:
        """Peek at new changes without advancing the read position."""
        return self._log.get_events_since(self._last_sequence)


class QueryBasedCDC:
    """
    Query-based CDC: polls the source using an updated_at timestamp.

    Simpler than log-based but has limitations:
    - Cannot detect deletes (no row to query).
    - Puts query load on the source database.
    - Requires an updated_at column on every table.
    - May miss rapid updates within the polling interval.
    """

    def __init__(self, timestamp_column: str = "updated_at") -> None:
        self.timestamp_column = timestamp_column
        self._last_poll: str | None = None

    def poll(self, source_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Query for records updated since the last poll.

        Returns changed records and advances the timestamp marker.
        """
        if self._last_poll is None:
            # First poll — return everything
            self._last_poll = datetime.now().isoformat()
            return [dict(r) for r in source_data]

        results = [
            dict(r) for r in source_data
            if r.get(self.timestamp_column, "") > self._last_poll
        ]
        self._last_poll = datetime.now().isoformat()
        return results

    @property
    def last_poll_time(self) -> str | None:
        return self._last_poll


class CDCConsumer:
    """
    Applies CDC events to a target store (upsert/delete).

    Maintains a materialized view of the source data by
    applying the stream of changes in order.
    """

    def __init__(self) -> None:
        self._target: dict[str, dict[str, Any]] = {}
        self._applied_count = 0
        self._insert_count = 0
        self._update_count = 0
        self._delete_count = 0

    @property
    def target_data(self) -> dict[str, dict[str, Any]]:
        return copy.deepcopy(self._target)

    @property
    def target_count(self) -> int:
        return len(self._target)

    @property
    def stats(self) -> dict[str, int]:
        return {
            "applied": self._applied_count,
            "inserts": self._insert_count,
            "updates": self._update_count,
            "deletes": self._delete_count,
        }

    def apply(self, events: list[CDCEvent]) -> int:
        """
        Apply a batch of CDC events to the target.

        Events are applied in order. Each event type maps to a
        specific operation on the target store.
        """
        count = 0
        for event in events:
            if event.operation == CDCOperation.INSERT:
                if event.after:
                    self._target[event.key] = copy.deepcopy(event.after)
                    self._insert_count += 1
            elif event.operation == CDCOperation.UPDATE:
                if event.after:
                    self._target[event.key] = copy.deepcopy(event.after)
                    self._update_count += 1
            elif event.operation == CDCOperation.DELETE:
                self._target.pop(event.key, None)
                self._delete_count += 1
            count += 1
            self._applied_count += 1
        return count
