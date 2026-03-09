"""
Data models for kafka-consumer-rides.

ArchiveRequest: batch of events to archive.
ArchiveStats: archive processing statistics.
ArchivedFile: metadata for a single archived file.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ArchiveRequest(BaseModel):
    """Batch of events to archive to MinIO Bronze layer."""

    events: list[dict] = Field(..., description="List of raw event dicts to archive")
    topic: str = Field("ride.events.v1", description="Source Kafka topic")


class ArchiveStats(BaseModel):
    """Archive processing statistics."""

    events_archived: int = 0
    files_written: int = 0
    bytes_written: int = 0
    errors: int = 0
    last_archived_at: Optional[str] = None
    uptime_seconds: float = 0.0


class ArchivedFile(BaseModel):
    """Metadata for a single archived file in MinIO."""

    file_path: str
    file_size: int
    event_count: int
    created_at: str
    topic: str
