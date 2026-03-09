"""
Batch prediction repository — in-memory job store.

Pre-seeds with 3 batch jobs: 1 completed (with results), 1 running, 1 pending.
"""

import random
import uuid
from typing import Optional

from models import BatchJob, BatchResult


class BatchPredictionRepository:
    """In-memory batch prediction job store."""

    def __init__(self, seed: bool = True):
        self._jobs: dict[str, BatchJob] = {}
        self._results: dict[str, list[BatchResult]] = {}
        self._rng = random.Random(42)
        if seed:
            self._seed()

    def _seed(self):
        """Pre-seed with 3 batch jobs."""
        # Completed job with results
        job1 = BatchJob(
            id="batch-001",
            model_name="fare_predictor",
            dataset_id="ds-rides-2024q1",
            status="completed",
            output_format="json",
            total_records=500,
            processed_records=500,
            created_at="2024-01-15T08:00:00+00:00",
            completed_at="2024-01-15T08:15:00+00:00",
        )
        self._jobs[job1.id] = job1

        # Generate results for completed job
        results = []
        for i in range(500):
            fare = round(self._rng.uniform(8.0, 65.0), 2)
            conf = round(self._rng.uniform(0.75, 0.98), 4)
            results.append(BatchResult(
                job_id=job1.id,
                entity_id=f"ride-{i+1:04d}",
                prediction=fare,
                confidence=conf,
            ))
        self._results[job1.id] = results

        # Running job
        job2 = BatchJob(
            id="batch-002",
            model_name="demand_predictor",
            dataset_id="ds-zones-2024q1",
            status="running",
            output_format="json",
            total_records=200,
            processed_records=120,
            created_at="2024-01-16T10:00:00+00:00",
        )
        self._jobs[job2.id] = job2

        # Pending job
        job3 = BatchJob(
            id="batch-003",
            model_name="eta_predictor",
            dataset_id="ds-routes-2024q1",
            status="pending",
            output_format="parquet",
            total_records=1000,
            processed_records=0,
            created_at="2024-01-16T12:00:00+00:00",
        )
        self._jobs[job3.id] = job3

    def create_job(self, model_name: str, dataset_id: str, output_format: str = "json") -> BatchJob:
        """Submit a new batch prediction job."""
        job_id = f"batch-{uuid.uuid4().hex[:8]}"
        total = self._rng.randint(100, 2000)
        job = BatchJob(
            id=job_id,
            model_name=model_name,
            dataset_id=dataset_id,
            status="pending",
            output_format=output_format,
            total_records=total,
            processed_records=0,
        )
        self._jobs[job_id] = job
        return job

    def list_jobs(self, status: Optional[str] = None) -> list[BatchJob]:
        """List batch jobs, optionally filtered by status."""
        jobs = list(self._jobs.values())
        if status:
            jobs = [j for j in jobs if j.status == status]
        return sorted(jobs, key=lambda j: j.created_at, reverse=True)

    def get_job(self, job_id: str) -> Optional[BatchJob]:
        """Get a batch job by ID."""
        return self._jobs.get(job_id)

    def get_results(self, job_id: str, page: int = 1, page_size: int = 50) -> tuple[list[BatchResult], int]:
        """Get paginated results for a batch job."""
        all_results = self._results.get(job_id, [])
        total = len(all_results)
        start = (page - 1) * page_size
        end = start + page_size
        return all_results[start:end], total

    def cancel_job(self, job_id: str) -> Optional[BatchJob]:
        """Cancel a batch job. Only pending/running jobs can be cancelled."""
        job = self._jobs.get(job_id)
        if job is None:
            return None
        if job.status in ("pending", "running"):
            job.status = "cancelled"
        return job


repo = BatchPredictionRepository(seed=True)
