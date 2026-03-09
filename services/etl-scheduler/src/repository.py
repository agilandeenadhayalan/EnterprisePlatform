"""
In-memory repository for ETL Scheduler service.

Manages scheduled jobs, execution history, and job state transitions
for ETL pipeline orchestration.
"""

import uuid
from datetime import datetime
from typing import Optional

from models import (
    ExecutionState,
    JobConfig,
    JobExecution,
    JobState,
    ScheduledJob,
)


class SchedulerRepository:
    def __init__(self):
        self._jobs: dict[str, ScheduledJob] = {}
        self._executions: dict[str, list[JobExecution]] = {}  # job_id -> executions

    def create_job(
        self,
        name: str,
        description: str,
        cron_expression: str,
        config: JobConfig,
        enabled: bool = True,
    ) -> ScheduledJob:
        job_id = str(uuid.uuid4())
        job = ScheduledJob(
            job_id=job_id,
            name=name,
            description=description,
            cron_expression=cron_expression,
            config=config,
            enabled=enabled,
        )
        self._jobs[job_id] = job
        self._executions[job_id] = []
        return job

    def get_job(self, job_id: str) -> Optional[ScheduledJob]:
        return self._jobs.get(job_id)

    def get_all_jobs(self) -> list[ScheduledJob]:
        return list(self._jobs.values())

    def update_job(
        self,
        job_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        cron_expression: Optional[str] = None,
        config: Optional[JobConfig] = None,
        enabled: Optional[bool] = None,
    ) -> Optional[ScheduledJob]:
        job = self._jobs.get(job_id)
        if not job:
            return None

        if name is not None:
            job.name = name
        if description is not None:
            job.description = description
        if cron_expression is not None:
            from models import CronSchedule
            job.cron_schedule = CronSchedule(cron_expression)
            job.next_run_at = job.cron_schedule.next_run()
        if config is not None:
            job.config = config
        if enabled is not None:
            job.enabled = enabled
            if not enabled:
                job.state = JobState.DISABLED
            elif job.state == JobState.DISABLED:
                job.state = JobState.IDLE

        job.updated_at = datetime.utcnow()
        return job

    def delete_job(self, job_id: str) -> bool:
        if job_id in self._jobs:
            del self._jobs[job_id]
            self._executions.pop(job_id, None)
            return True
        return False

    def trigger_job(self, job_id: str) -> Optional[JobExecution]:
        job = self._jobs.get(job_id)
        if not job:
            return None

        execution_id = str(uuid.uuid4())
        execution = JobExecution(
            execution_id=execution_id,
            job_id=job_id,
            state=ExecutionState.RUNNING,
            started_at=datetime.utcnow(),
        )

        job.state = JobState.RUNNING
        job.last_run_at = datetime.utcnow()

        if job_id not in self._executions:
            self._executions[job_id] = []
        self._executions[job_id].append(execution)

        # Simulate completion
        import random
        execution.state = ExecutionState.COMPLETED
        execution.rows_processed = random.randint(100, 100000)
        execution.completed_at = datetime.utcnow()
        execution.duration_seconds = random.uniform(1.0, 120.0)

        job.state = JobState.IDLE
        job.next_run_at = job.cron_schedule.next_run()

        return execution

    def get_job_history(self, job_id: str) -> list[JobExecution]:
        return self._executions.get(job_id, [])

    def job_exists(self, job_id: str) -> bool:
        return job_id in self._jobs


# Singleton
scheduler_repo = SchedulerRepository()
