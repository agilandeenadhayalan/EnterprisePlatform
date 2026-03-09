"""
Pydantic request/response schemas for the data lake writer API.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class LayerEnum(str, Enum):
    """Valid Medallion architecture layers."""
    bronze = "bronze"
    silver = "silver"
    gold = "gold"


# ── Request schemas ──

class WriteRequest(BaseModel):
    """POST /write/{layer} — write data to a specific layer."""
    source: str = Field(..., description="Source system name (e.g., 'gps-tracker', 'ride-service')")
    data: dict[str, Any] = Field(..., description="Raw data payload to store")
    metadata: Optional[dict[str, Any]] = Field(default=None, description="Optional metadata")


class TransformRequest(BaseModel):
    """Request body for transform operations (optional filters)."""
    source_filter: Optional[str] = Field(default=None, description="Filter by source system")
    limit: Optional[int] = Field(default=None, description="Max records to transform")


# ── Response schemas ──

class WriteResponse(BaseModel):
    """Response after writing data to a layer."""
    record_id: str
    layer: str
    source: str
    timestamp: datetime
    message: str = "Record written successfully"


class RecordResponse(BaseModel):
    """A single Medallion record."""
    record_id: str
    layer: str
    source: str
    data: dict[str, Any]
    timestamp: datetime
    metadata: dict[str, Any] = {}


class LayerStatsResponse(BaseModel):
    """Stats for a single layer."""
    layer: str
    object_count: int
    total_size_bytes: int


class AllLayersStatsResponse(BaseModel):
    """Stats for all layers."""
    layers: list[LayerStatsResponse]
    total_objects: int
    total_size_bytes: int


class TransformJobResponse(BaseModel):
    """Response for a transform operation."""
    job_id: str
    source_layer: str
    target_layer: str
    status: str
    records_in: int
    records_out: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
