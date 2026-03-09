"""
Pydantic request/response schemas for the data export API.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Request schemas ──


class ExportRequest(BaseModel):
    """POST /export — start a new export job."""
    query: str = Field(..., description="Query to export (SQL or named query)")
    format: str = Field(default="csv", description="Export format: csv, parquet, json, xlsx")
    destination: str = Field(default="download", description="Destination: download or minio path")


# ── Response schemas ──


class ExportFormatResponse(BaseModel):
    """Supported export format."""
    format_id: str
    name: str
    description: str
    content_type: str
    extension: str


class ExportFormatListResponse(BaseModel):
    """List of supported export formats."""
    formats: list[ExportFormatResponse]
    total: int


class ExportJobResponse(BaseModel):
    """Export job details."""
    id: str
    query: str
    format: str
    destination: str
    status: str
    row_count: int
    file_size_bytes: int
    download_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class ExportJobListResponse(BaseModel):
    """List of export jobs."""
    jobs: list[ExportJobResponse]
    total: int
