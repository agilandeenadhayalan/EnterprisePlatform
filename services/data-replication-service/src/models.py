"""
Domain models for the data replication service.

Manages replication jobs between ClickHouse and MinIO.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional


class ReplicationDirection(str, Enum):
    """Direction of data replication."""
    CH_TO_MINIO = "ch_to_minio"
    MINIO_TO_CH = "minio_to_ch"


class ReplicationJob:
    """A data replication job."""

    def __init__(
        self,
        id: str,
        direction: str,
        source: str,
        destination: str,
        status: str = "pending",
        records_total: int = 0,
        records_processed: int = 0,
        bytes_transferred: int = 0,
        format: str = "parquet",
        created_at: Optional[datetime] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        error: Optional[str] = None,
    ):
        self.id = id
        self.direction = direction
        self.source = source
        self.destination = destination
        self.status = status  # pending, running, completed, failed, cancelled
        self.records_total = records_total
        self.records_processed = records_processed
        self.bytes_transferred = bytes_transferred
        self.format = format
        self.created_at = created_at or datetime.utcnow()
        self.started_at = started_at
        self.completed_at = completed_at
        self.error = error

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "direction": self.direction,
            "source": self.source,
            "destination": self.destination,
            "status": self.status,
            "records_total": self.records_total,
            "records_processed": self.records_processed,
            "bytes_transferred": self.bytes_transferred,
            "format": self.format,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
        }
