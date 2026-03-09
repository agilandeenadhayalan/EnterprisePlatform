"""
In-memory repository for CDC Connector service.

Manages table tracking, watermarks, and CDC stream state for
watermark-based Change Data Capture from PostgreSQL.
"""

import random
import uuid
from datetime import datetime
from typing import Optional

from models import CDCConfig, CDCEvent, CDCStream, ChangeType, StreamState, TableTracker


class CDCRepository:
    def __init__(self):
        self._trackers: dict[str, TableTracker] = {}
        self._events: dict[str, list[CDCEvent]] = {}  # table_name -> events

    def register_table(
        self,
        table_name: str,
        schema_name: str = "public",
        config: Optional[CDCConfig] = None,
    ) -> TableTracker:
        tracker = TableTracker(
            table_name=table_name,
            schema_name=schema_name,
            config=config or CDCConfig(),
            state=StreamState.ACTIVE,
            registered_at=datetime.utcnow(),
        )
        self._trackers[table_name] = tracker
        self._events[table_name] = []
        return tracker

    def unregister_table(self, table_name: str) -> bool:
        if table_name in self._trackers:
            del self._trackers[table_name]
            self._events.pop(table_name, None)
            return True
        return False

    def get_tracker(self, table_name: str) -> Optional[TableTracker]:
        return self._trackers.get(table_name)

    def get_all_trackers(self) -> list[TableTracker]:
        return list(self._trackers.values())

    def table_registered(self, table_name: str) -> bool:
        return table_name in self._trackers

    def sync_table(self, table_name: str) -> tuple[int, list[CDCEvent]]:
        """Simulate polling for changes and producing CDC events."""
        tracker = self._trackers.get(table_name)
        if not tracker:
            return 0, []

        # Simulate capturing changes
        num_changes = random.randint(5, 500)
        events = []
        change_types = [ChangeType.INSERT, ChangeType.UPDATE, ChangeType.DELETE]

        for _ in range(num_changes):
            event = CDCEvent(
                event_id=str(uuid.uuid4()),
                table_name=table_name,
                change_type=random.choice(change_types),
                row_id=str(uuid.uuid4()),
                captured_at=datetime.utcnow(),
            )
            events.append(event)

        # Update tracker
        tracker.last_watermark = datetime.utcnow()
        tracker.total_changes_captured += num_changes
        tracker.last_poll_at = datetime.utcnow()

        # Store events
        if table_name not in self._events:
            self._events[table_name] = []
        self._events[table_name].extend(events)

        return num_changes, events

    def get_stream_status(self, table_name: str) -> Optional[CDCStream]:
        tracker = self._trackers.get(table_name)
        if not tracker:
            return None

        return CDCStream(
            table_name=tracker.table_name,
            state=tracker.state,
            events_captured=tracker.total_changes_captured,
            events_per_second=random.uniform(0, 100) if tracker.state == StreamState.ACTIVE else 0,
            last_event_at=tracker.last_poll_at,
            lag_seconds=random.uniform(0, 5) if tracker.state == StreamState.ACTIVE else 0,
        )

    def get_all_stream_statuses(self) -> list[CDCStream]:
        return [
            self.get_stream_status(t.table_name)
            for t in self._trackers.values()
        ]

    def get_active_count(self) -> int:
        return sum(1 for t in self._trackers.values() if t.state == StreamState.ACTIVE)

    def get_total_events(self) -> int:
        return sum(t.total_changes_captured for t in self._trackers.values())


# Singleton
cdc_repo = CDCRepository()
