"""
Pydantic schemas for CDC Connector API request/response validation.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CDCConfigSchema(BaseModel):
    watermark_column: str = Field(default="updated_at", description="Column to track changes")
    poll_interval_seconds: int = Field(default=30, ge=5, le=3600, description="Polling interval")
    batch_size: int = Field(default=1000, ge=100, le=100000, description="Batch size per poll")
    kafka_topic: str = Field(default="etl.cdc.events.v1", description="Kafka topic for CDC events")


class RegisterTableRequest(BaseModel):
    schema_name: str = Field(default="public", description="PostgreSQL schema")
    config: CDCConfigSchema = Field(default_factory=CDCConfigSchema)


class TableTrackerResponse(BaseModel):
    table_name: str
    schema_name: str
    config: CDCConfigSchema
    state: str
    last_watermark: Optional[datetime] = None
    total_changes_captured: int = 0
    last_poll_at: Optional[datetime] = None
    registered_at: Optional[datetime] = None


class TablesListResponse(BaseModel):
    tables: list[TableTrackerResponse]
    total: int


class CDCStreamResponse(BaseModel):
    table_name: str
    state: str
    events_captured: int = 0
    events_per_second: float = 0.0
    last_event_at: Optional[datetime] = None
    lag_seconds: float = 0.0


class CDCStatusResponse(BaseModel):
    streams: list[CDCStreamResponse]
    total_tables: int
    active_streams: int
    total_events_captured: int


class SyncResponse(BaseModel):
    table_name: str
    changes_captured: int
    new_watermark: Optional[datetime] = None
    kafka_topic: str
    message: str
