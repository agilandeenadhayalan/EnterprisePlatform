"""
Pydantic request/response schemas for the data replication API.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Request schemas ──

class ReplicationRequest(BaseModel):
    """POST /replicate — start a replication job."""
    direction: str = Field(..., description="Replication direction: ch_to_minio or minio_to_ch")
    source: str = Field(..., description="Source table/bucket path")
    destination: str = Field(..., description="Destination bucket path/table")
    format: str = Field(default="parquet", description="Output format (parquet, csv, json)")


# ── Response schemas ──

class ReplicationJobResponse(BaseModel):
    """A replication job."""
    id: str
    direction: str
    source: str
    destination: str
    status: str
    records_total: int
    records_processed: int
    bytes_transferred: int
    format: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class ReplicationJobListResponse(BaseModel):
    """List of replication jobs."""
    jobs: list[ReplicationJobResponse]
    total: int
