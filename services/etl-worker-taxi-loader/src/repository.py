"""
In-memory repository for ETL Worker Taxi Loader service.

Manages load jobs, checkpoint tracking, and job history for NYC taxi
data loading into ClickHouse fact_rides table.
"""

import uuid
from datetime import datetime
from typing import Optional

from models import LoadCheckpoint, LoadJob, LoadState


class TaxiLoaderRepository:
    def __init__(self):
        self._jobs: dict[str, LoadJob] = {}
        self._checkpoints: dict[str, LoadCheckpoint] = {}  # key: "year-month"

    def _checkpoint_key(self, year: int, month: int) -> str:
        return f"{year}-{month:02d}"

    def create_load_job(self, year: int, month: int, batch_size: int = 100000) -> LoadJob:
        job_id = str(uuid.uuid4())
        filename = f"yellow_tripdata_{year}-{month:02d}.parquet"
        job = LoadJob(
            job_id=job_id,
            year=year,
            month=month,
            state=LoadState.RUNNING,
            current_file=filename,
            started_at=datetime.utcnow(),
        )
        self._jobs[job_id] = job
        return job

    def complete_job(self, job_id: str, rows_loaded: int, speed: float = 0.0) -> Optional[LoadJob]:
        job = self._jobs.get(job_id)
        if not job:
            return None
        job.state = LoadState.COMPLETED
        job.rows_loaded = rows_loaded
        job.total_rows = rows_loaded
        job.speed_rows_per_sec = speed
        job.completed_at = datetime.utcnow()

        # Update checkpoint
        key = self._checkpoint_key(job.year, job.month)
        self._checkpoints[key] = LoadCheckpoint(
            year=job.year,
            month=job.month,
            last_row_offset=rows_loaded,
            last_file=job.current_file,
            rows_loaded=rows_loaded,
            updated_at=datetime.utcnow(),
        )

        return job

    def fail_job(self, job_id: str, error_message: str) -> Optional[LoadJob]:
        job = self._jobs.get(job_id)
        if not job:
            return None
        job.state = LoadState.FAILED
        job.error_message = error_message
        job.completed_at = datetime.utcnow()
        return job

    def get_job(self, job_id: str) -> Optional[LoadJob]:
        return self._jobs.get(job_id)

    def get_all_jobs(self) -> list[LoadJob]:
        return list(self._jobs.values())

    def get_active_jobs(self) -> list[LoadJob]:
        return [j for j in self._jobs.values() if j.state == LoadState.RUNNING]

    def get_completed_jobs(self) -> list[LoadJob]:
        return [j for j in self._jobs.values() if j.state == LoadState.COMPLETED]

    def get_checkpoint(self, year: int, month: int) -> Optional[LoadCheckpoint]:
        return self._checkpoints.get(self._checkpoint_key(year, month))

    def get_all_checkpoints(self) -> list[LoadCheckpoint]:
        return list(self._checkpoints.values())

    def get_total_rows_loaded(self) -> int:
        return sum(j.rows_loaded for j in self._jobs.values() if j.state == LoadState.COMPLETED)


# Singleton
taxi_loader_repo = TaxiLoaderRepository()
