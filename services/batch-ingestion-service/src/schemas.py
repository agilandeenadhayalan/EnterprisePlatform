"""
Pydantic schemas for Batch Ingestion Service API request/response validation.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class FileMetadataSchema(BaseModel):
    filename: str = Field(..., description="Name of the file")
    format: str = Field(..., description="File format: csv, parquet, json, avro")
    size_bytes: int = Field(..., ge=0, description="File size in bytes")
    row_count: Optional[int] = Field(None, ge=0, description="Number of rows")
    schema_name: Optional[str] = None
    source: Optional[str] = None


class IngestRequest(BaseModel):
    schema_name: str = Field(..., description="Schema name for validation")
    source: str = Field(..., description="Data source identifier")
    files: list[FileMetadataSchema] = Field(..., min_length=1, description="Files to ingest")
    target_layer: str = Field(default="bronze", description="Target data lake layer")


class IngestionStatsResponse(BaseModel):
    files_processed: int = 0
    total_bytes: int = 0
    total_rows: int = 0
    failed_files: int = 0


class IngestionJobResponse(BaseModel):
    job_id: str
    schema_name: str
    source: str
    target_layer: str
    state: str
    stats: IngestionStatsResponse
    minio_path: Optional[str] = None
    event_produced: bool = False
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class IngestionHistoryResponse(BaseModel):
    jobs: list[IngestionJobResponse]
    total: int


class SchemaDefinition(BaseModel):
    name: str
    description: str
    required_columns: list[str]
    formats: list[str]


class SchemasListResponse(BaseModel):
    schemas: list[SchemaDefinition]
    total: int
