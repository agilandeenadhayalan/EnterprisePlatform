"""
Data Replication repository — in-memory replication job tracking.

Simulates replication between ClickHouse and MinIO with job management.
"""

import random
import uuid
from datetime import datetime
from typing import Optional

from models import ReplicationJob


class ReplicationRepository:
    """In-memory replication job storage."""

    def __init__(self):
        self._jobs: dict[str, ReplicationJob] = {}

    def create_job(
        self,
        direction: str,
        source: str,
        destination: str,
        format: str = "parquet",
    ) -> ReplicationJob:
        """Create and simulate a replication job."""
        job_id = str(uuid.uuid4())

        # Simulate a completed replication
        records = random.randint(1000, 100000)
        bytes_transferred = records * random.randint(100, 500)

        job = ReplicationJob(
            id=job_id,
            direction=direction,
            source=source,
            destination=destination,
            status="completed",
            records_total=records,
            records_processed=records,
            bytes_transferred=bytes_transferred,
            format=format,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )
        self._jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> Optional[ReplicationJob]:
        """Get a replication job by ID."""
        return self._jobs.get(job_id)

    def list_jobs(self) -> list[ReplicationJob]:
        """List all replication jobs."""
        return list(self._jobs.values())

    def cancel_job(self, job_id: str) -> Optional[ReplicationJob]:
        """Cancel a running replication job."""
        job = self._jobs.get(job_id)
        if not job:
            return None
        if job.status in ("completed", "failed", "cancelled"):
            return job  # Cannot cancel already-finished jobs
        job.status = "cancelled"
        job.completed_at = datetime.utcnow()
        return job


# Singleton repository instance
repo = ReplicationRepository()
