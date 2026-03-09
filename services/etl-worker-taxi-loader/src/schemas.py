"""
Pydantic schemas for ETL Worker Taxi Loader API request/response validation.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class LoadRequest(BaseModel):
    year: int = Field(..., ge=2009, le=2030, description="Year of taxi data")
    month: int = Field(..., ge=1, le=12, description="Month of taxi data")
    batch_size: int = Field(default=100000, ge=1000, le=1000000, description="Rows per batch")


class LoadJobResponse(BaseModel):
    job_id: str
    year: int
    month: int
    state: str
    rows_loaded: int
    total_rows: Optional[int] = None
    current_file: Optional[str] = None
    speed_rows_per_sec: float = 0.0
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class LoadStatusResponse(BaseModel):
    active_jobs: list[LoadJobResponse] = []
    completed_jobs: int = 0
    total_rows_loaded: int = 0


class CheckpointResponse(BaseModel):
    year: int
    month: int
    last_row_offset: int
    last_file: Optional[str] = None
    rows_loaded: int
    updated_at: Optional[datetime] = None


class CheckpointsListResponse(BaseModel):
    checkpoints: list[CheckpointResponse] = []
    total: int = 0
