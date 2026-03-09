"""
Pydantic request/response schemas for the data catalog API.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Request schemas ──

class DatasetCreate(BaseModel):
    """POST /catalog/datasets — register a new dataset."""
    name: str = Field(..., description="Dataset name")
    description: str = Field(..., description="Dataset description")
    store: str = Field(..., description="Storage backend (clickhouse, minio, postgres)")
    location: str = Field(..., description="Table name or bucket/path")
    schema_fields: Optional[list[dict[str, str]]] = Field(default=None, description="Schema field definitions")
    format: str = Field(default="parquet", description="Data format")
    owner: Optional[str] = Field(default=None, description="Dataset owner")
    tags: Optional[list[str]] = Field(default=None, description="Searchable tags")
    size_bytes: int = Field(default=0, description="Dataset size in bytes")
    record_count: int = Field(default=0, description="Number of records")


class DatasetUpdate(BaseModel):
    """PATCH /catalog/datasets/{id} — update dataset metadata."""
    name: Optional[str] = None
    description: Optional[str] = None
    store: Optional[str] = None
    location: Optional[str] = None
    schema_fields: Optional[list[dict[str, str]]] = None
    format: Optional[str] = None
    owner: Optional[str] = None
    tags: Optional[list[str]] = None
    size_bytes: Optional[int] = None
    record_count: Optional[int] = None


# ── Response schemas ──

class DatasetResponse(BaseModel):
    """Full dataset record."""
    id: str
    name: str
    description: str
    store: str
    location: str
    schema_fields: list[dict[str, str]] = []
    format: str
    owner: Optional[str] = None
    tags: list[str] = []
    size_bytes: int
    record_count: int
    created_at: datetime
    updated_at: datetime


class DatasetListResponse(BaseModel):
    """List of datasets."""
    datasets: list[DatasetResponse]
    total: int


class CatalogStatsResponse(BaseModel):
    """Catalog statistics."""
    total_datasets: int
    by_store: dict[str, int]
    total_size_bytes: int
    total_records: int
