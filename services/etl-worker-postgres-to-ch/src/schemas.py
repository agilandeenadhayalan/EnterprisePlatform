"""
Pydantic schemas for ETL Worker Postgres-to-ClickHouse API request/response validation.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SyncRequest(BaseModel):
    mode: str = Field(default="incremental", description="Sync mode: incremental or full")
    batch_size: int = Field(default=10000, ge=100, le=1000000, description="Rows per batch")


class SyncJobResponse(BaseModel):
    job_id: str
    table_name: str
    mode: str
    state: str
    rows_synced: int
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class SyncStatusResponse(BaseModel):
    total_jobs: int
    running_jobs: int
    completed_jobs: int
    failed_jobs: int
    jobs: list[SyncJobResponse] = []


class TableWatermarkResponse(BaseModel):
    table_name: str
    last_watermark: Optional[datetime] = None
    rows_synced: int = 0
    last_sync_at: Optional[datetime] = None


class SyncTablesResponse(BaseModel):
    tables: list[TableWatermarkResponse]
    total: int


class FullSyncRequest(BaseModel):
    table_name: str = Field(..., description="Table name to fully resync")
    batch_size: int = Field(default=10000, ge=100, le=1000000)
