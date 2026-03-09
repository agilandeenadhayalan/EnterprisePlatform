"""
Domain models for the data lake writer service.

Represents the Medallion architecture layers (Bronze/Silver/Gold) and
data records flowing through the data lake pipeline.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional


class Layer(str, Enum):
    """Medallion architecture layers."""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"


class MedallionRecord:
    """A record stored in a Medallion layer."""

    def __init__(
        self,
        record_id: str,
        layer: str,
        source: str,
        data: dict[str, Any],
        timestamp: Optional[datetime] = None,
        metadata: Optional[dict[str, Any]] = None,
    ):
        self.record_id = record_id
        self.layer = layer
        self.source = source
        self.data = data
        self.timestamp = timestamp or datetime.utcnow()
        self.metadata = metadata or {}

    def to_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "layer": self.layer,
            "source": self.source,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


class TransformJob:
    """Tracks a transformation job between layers."""

    def __init__(
        self,
        job_id: str,
        source_layer: str,
        target_layer: str,
        status: str = "pending",
        records_in: int = 0,
        records_out: int = 0,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        error: Optional[str] = None,
    ):
        self.job_id = job_id
        self.source_layer = source_layer
        self.target_layer = target_layer
        self.status = status
        self.records_in = records_in
        self.records_out = records_out
        self.started_at = started_at or datetime.utcnow()
        self.completed_at = completed_at
        self.error = error

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "source_layer": self.source_layer,
            "target_layer": self.target_layer,
            "status": self.status,
            "records_in": self.records_in,
            "records_out": self.records_out,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
        }


class LayerStats:
    """Statistics for a single Medallion layer."""

    def __init__(self, layer: str, object_count: int = 0, total_size_bytes: int = 0):
        self.layer = layer
        self.object_count = object_count
        self.total_size_bytes = total_size_bytes

    def to_dict(self) -> dict:
        return {
            "layer": self.layer,
            "object_count": self.object_count,
            "total_size_bytes": self.total_size_bytes,
        }
