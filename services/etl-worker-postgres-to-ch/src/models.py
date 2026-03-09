"""
Domain models for ETL Worker Postgres-to-ClickHouse service.

Tracks sync jobs, their statuses, configuration, and per-table watermarks
used for incremental data synchronization.
"""

from datetime import datetime
from enum import Enum
from typing import Optional


class SyncMode(str, Enum):
    INCREMENTAL = "incremental"
    FULL = "full"


class SyncState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SyncJob:
    def __init__(
        self,
        job_id: str,
        table_name: str,
        mode: SyncMode = SyncMode.INCREMENTAL,
        state: SyncState = SyncState.PENDING,
        rows_synced: int = 0,
        error_message: Optional[str] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
    ):
        self.job_id = job_id
        self.table_name = table_name
        self.mode = mode
        self.state = state
        self.rows_synced = rows_synced
        self.error_message = error_message
        self.started_at = started_at or datetime.utcnow()
        self.completed_at = completed_at


class SyncStatus:
    def __init__(
        self,
        total_jobs: int = 0,
        running_jobs: int = 0,
        completed_jobs: int = 0,
        failed_jobs: int = 0,
    ):
        self.total_jobs = total_jobs
        self.running_jobs = running_jobs
        self.completed_jobs = completed_jobs
        self.failed_jobs = failed_jobs


class SyncConfig:
    def __init__(
        self,
        table_name: str,
        source_schema: str = "public",
        watermark_column: str = "updated_at",
        batch_size: int = 10000,
        enabled: bool = True,
    ):
        self.table_name = table_name
        self.source_schema = source_schema
        self.watermark_column = watermark_column
        self.batch_size = batch_size
        self.enabled = enabled


class TableWatermark:
    def __init__(
        self,
        table_name: str,
        last_watermark: Optional[datetime] = None,
        rows_synced: int = 0,
        last_sync_at: Optional[datetime] = None,
    ):
        self.table_name = table_name
        self.last_watermark = last_watermark
        self.rows_synced = rows_synced
        self.last_sync_at = last_sync_at
