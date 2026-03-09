"""
In-memory repository for ETL Worker Postgres-to-ClickHouse service.

Manages sync jobs, watermark tracking, and job history using in-memory
data structures. In production, this would use Redis or a database.
"""

import uuid
from datetime import datetime
from typing import Optional

from models import SyncJob, SyncMode, SyncState, TableWatermark


# Default syncable tables from the mobility platform schema
DEFAULT_TABLES = [
    "users",
    "drivers",
    "vehicles",
    "rides",
    "payments",
    "locations",
    "ride_events",
    "driver_locations",
]


class SyncRepository:
    def __init__(self):
        self._jobs: dict[str, SyncJob] = {}
        self._watermarks: dict[str, TableWatermark] = {}
        self._init_default_tables()

    def _init_default_tables(self):
        for table in DEFAULT_TABLES:
            self._watermarks[table] = TableWatermark(table_name=table)

    def create_sync_job(
        self,
        table_name: str,
        mode: SyncMode = SyncMode.INCREMENTAL,
        batch_size: int = 10000,
    ) -> SyncJob:
        job_id = str(uuid.uuid4())
        job = SyncJob(
            job_id=job_id,
            table_name=table_name,
            mode=mode,
            state=SyncState.RUNNING,
            started_at=datetime.utcnow(),
        )
        self._jobs[job_id] = job

        # Ensure the table has a watermark entry
        if table_name not in self._watermarks:
            self._watermarks[table_name] = TableWatermark(table_name=table_name)

        return job

    def complete_job(self, job_id: str, rows_synced: int) -> Optional[SyncJob]:
        job = self._jobs.get(job_id)
        if not job:
            return None
        job.state = SyncState.COMPLETED
        job.rows_synced = rows_synced
        job.completed_at = datetime.utcnow()

        # Update watermark
        wm = self._watermarks.get(job.table_name)
        if wm:
            wm.last_watermark = datetime.utcnow()
            wm.rows_synced += rows_synced
            wm.last_sync_at = datetime.utcnow()

        return job

    def fail_job(self, job_id: str, error_message: str) -> Optional[SyncJob]:
        job = self._jobs.get(job_id)
        if not job:
            return None
        job.state = SyncState.FAILED
        job.error_message = error_message
        job.completed_at = datetime.utcnow()
        return job

    def get_job(self, job_id: str) -> Optional[SyncJob]:
        return self._jobs.get(job_id)

    def get_all_jobs(self) -> list[SyncJob]:
        return list(self._jobs.values())

    def get_jobs_by_state(self, state: SyncState) -> list[SyncJob]:
        return [j for j in self._jobs.values() if j.state == state]

    def get_watermark(self, table_name: str) -> Optional[TableWatermark]:
        return self._watermarks.get(table_name)

    def get_all_watermarks(self) -> list[TableWatermark]:
        return list(self._watermarks.values())

    def reset_watermark(self, table_name: str) -> Optional[TableWatermark]:
        wm = self._watermarks.get(table_name)
        if wm:
            wm.last_watermark = None
            wm.rows_synced = 0
            wm.last_sync_at = None
        return wm

    def table_exists(self, table_name: str) -> bool:
        return table_name in self._watermarks

    def add_table(self, table_name: str) -> TableWatermark:
        if table_name not in self._watermarks:
            self._watermarks[table_name] = TableWatermark(table_name=table_name)
        return self._watermarks[table_name]


# Singleton repository instance
sync_repo = SyncRepository()
