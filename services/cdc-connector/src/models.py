"""
Domain models for CDC Connector service.

Represents CDC streams, change events, configuration, and per-table
tracking state for watermark-based Change Data Capture from PostgreSQL.
"""

from datetime import datetime
from enum import Enum
from typing import Optional


class StreamState(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    STOPPED = "stopped"


class ChangeType(str, Enum):
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"


class CDCConfig:
    def __init__(
        self,
        watermark_column: str = "updated_at",
        poll_interval_seconds: int = 30,
        batch_size: int = 1000,
        kafka_topic: str = "etl.cdc.events.v1",
    ):
        self.watermark_column = watermark_column
        self.poll_interval_seconds = poll_interval_seconds
        self.batch_size = batch_size
        self.kafka_topic = kafka_topic


class TableTracker:
    def __init__(
        self,
        table_name: str,
        schema_name: str = "public",
        config: Optional[CDCConfig] = None,
        state: StreamState = StreamState.ACTIVE,
        last_watermark: Optional[datetime] = None,
        total_changes_captured: int = 0,
        last_poll_at: Optional[datetime] = None,
        registered_at: Optional[datetime] = None,
    ):
        self.table_name = table_name
        self.schema_name = schema_name
        self.config = config or CDCConfig()
        self.state = state
        self.last_watermark = last_watermark
        self.total_changes_captured = total_changes_captured
        self.last_poll_at = last_poll_at
        self.registered_at = registered_at or datetime.utcnow()


class CDCEvent:
    def __init__(
        self,
        event_id: str,
        table_name: str,
        change_type: ChangeType,
        row_id: Optional[str] = None,
        old_values: Optional[dict] = None,
        new_values: Optional[dict] = None,
        captured_at: Optional[datetime] = None,
    ):
        self.event_id = event_id
        self.table_name = table_name
        self.change_type = change_type
        self.row_id = row_id
        self.old_values = old_values
        self.new_values = new_values
        self.captured_at = captured_at or datetime.utcnow()


class CDCStream:
    def __init__(
        self,
        table_name: str,
        state: StreamState,
        events_captured: int = 0,
        events_per_second: float = 0.0,
        last_event_at: Optional[datetime] = None,
        lag_seconds: float = 0.0,
    ):
        self.table_name = table_name
        self.state = state
        self.events_captured = events_captured
        self.events_per_second = events_per_second
        self.last_event_at = last_event_at
        self.lag_seconds = lag_seconds
