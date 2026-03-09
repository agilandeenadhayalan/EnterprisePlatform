"""
Pydantic request/response schemas for the kafka-consumer-rides API.
"""

from typing import Optional

from pydantic import BaseModel, Field


# -- Request schemas --


class ArchiveBatchRequest(BaseModel):
    """POST /archive — batch of events to archive."""

    events: list[dict] = Field(..., description="List of raw event dicts to archive")
    topic: str = Field("ride.events.v1", description="Source Kafka topic")


# -- Response schemas --


class ArchiveBatchResponse(BaseModel):
    """POST /archive response."""

    archived: int
    file_path: str
    file_size: int
    status: str


class ArchiveStatsResponse(BaseModel):
    """GET /archive/stats response."""

    events_archived: int
    files_written: int
    bytes_written: int
    errors: int
    last_archived_at: Optional[str] = None
    uptime_seconds: float


class ArchivedFileResponse(BaseModel):
    """Single archived file info."""

    file_path: str
    file_size: int
    event_count: int
    created_at: str
    topic: str


class ArchivedFilesListResponse(BaseModel):
    """GET /archive/files response."""

    files: list[ArchivedFileResponse]
    total: int
