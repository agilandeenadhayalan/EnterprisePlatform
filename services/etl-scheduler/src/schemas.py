"""
Pydantic schemas for ETL Scheduler API request/response validation.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class JobConfigSchema(BaseModel):
    target_service: str = Field(..., description="Service to call (e.g., etl-worker-postgres-to-ch)")
    target_endpoint: str = Field(..., description="Endpoint to call (e.g., /sync/users)")
    payload: dict = Field(default={}, description="Request body payload")
    timeout_seconds: int = Field(default=3600, ge=30, le=86400)
    retry_count: int = Field(default=3, ge=0, le=10)
    retry_delay_seconds: int = Field(default=60, ge=10, le=3600)


class CreateJobRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Job name")
    description: str = Field(default="", max_length=1000, description="Job description")
    cron_expression: str = Field(..., description="Cron schedule (5 fields: min hour dom month dow)")
    config: JobConfigSchema
    enabled: bool = Field(default=True)


class UpdateJobRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    cron_expression: Optional[str] = None
    config: Optional[JobConfigSchema] = None
    enabled: Optional[bool] = None


class CronScheduleResponse(BaseModel):
    expression: str
    minute: str
    hour: str
    day_of_month: str
    month: str
    day_of_week: str


class JobResponse(BaseModel):
    job_id: str
    name: str
    description: str
    cron_schedule: CronScheduleResponse
    config: JobConfigSchema
    state: str
    enabled: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None


class JobListResponse(BaseModel):
    jobs: list[JobResponse]
    total: int


class ExecutionResponse(BaseModel):
    execution_id: str
    job_id: str
    state: str
    rows_processed: int
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0


class ExecutionHistoryResponse(BaseModel):
    executions: list[ExecutionResponse]
    total: int


class TriggerResponse(BaseModel):
    execution_id: str
    job_id: str
    message: str
    state: str
