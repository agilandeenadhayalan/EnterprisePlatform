"""
Domain models for ETL Scheduler service.

Represents scheduled jobs, their executions, configurations,
and cron schedule parsing for ETL pipeline orchestration.
"""

from datetime import datetime
from enum import Enum
from typing import Optional


class JobState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DISABLED = "disabled"


class ExecutionState(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class CronSchedule:
    """Simple cron expression parser supporting minute, hour, day, month, weekday."""

    def __init__(self, expression: str):
        self.expression = expression
        parts = expression.strip().split()
        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression: {expression}. Expected 5 fields.")
        self.minute = parts[0]
        self.hour = parts[1]
        self.day_of_month = parts[2]
        self.month = parts[3]
        self.day_of_week = parts[4]

    def next_run(self, after: Optional[datetime] = None) -> datetime:
        """Calculate the next run time after the given datetime.

        This is a simplified calculation that advances by the minimum
        interval implied by the cron expression.
        """
        from datetime import timedelta
        base = after or datetime.utcnow()

        # Simple next-run: advance by 1 hour for hourly, 1 day for daily, etc.
        if self.minute != "*" and self.hour == "*":
            # Runs every hour at specific minute
            next_time = base.replace(second=0, microsecond=0) + timedelta(hours=1)
        elif self.minute != "*" and self.hour != "*":
            # Runs daily at specific time
            next_time = base.replace(
                hour=int(self.hour), minute=int(self.minute), second=0, microsecond=0
            )
            if next_time <= base:
                next_time += timedelta(days=1)
        else:
            # Default: next minute
            next_time = base.replace(second=0, microsecond=0) + timedelta(minutes=1)

        return next_time

    def to_dict(self) -> dict:
        return {
            "expression": self.expression,
            "minute": self.minute,
            "hour": self.hour,
            "day_of_month": self.day_of_month,
            "month": self.month,
            "day_of_week": self.day_of_week,
        }


class JobConfig:
    def __init__(
        self,
        target_service: str,
        target_endpoint: str,
        payload: Optional[dict] = None,
        timeout_seconds: int = 3600,
        retry_count: int = 3,
        retry_delay_seconds: int = 60,
    ):
        self.target_service = target_service
        self.target_endpoint = target_endpoint
        self.payload = payload or {}
        self.timeout_seconds = timeout_seconds
        self.retry_count = retry_count
        self.retry_delay_seconds = retry_delay_seconds


class ScheduledJob:
    def __init__(
        self,
        job_id: str,
        name: str,
        description: str,
        cron_expression: str,
        config: JobConfig,
        state: JobState = JobState.IDLE,
        enabled: bool = True,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        last_run_at: Optional[datetime] = None,
        next_run_at: Optional[datetime] = None,
    ):
        self.job_id = job_id
        self.name = name
        self.description = description
        self.cron_schedule = CronSchedule(cron_expression)
        self.config = config
        self.state = state
        self.enabled = enabled
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.last_run_at = last_run_at
        self.next_run_at = next_run_at or self.cron_schedule.next_run()


class JobExecution:
    def __init__(
        self,
        execution_id: str,
        job_id: str,
        state: ExecutionState = ExecutionState.RUNNING,
        rows_processed: int = 0,
        error_message: Optional[str] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        duration_seconds: float = 0.0,
    ):
        self.execution_id = execution_id
        self.job_id = job_id
        self.state = state
        self.rows_processed = rows_processed
        self.error_message = error_message
        self.started_at = started_at or datetime.utcnow()
        self.completed_at = completed_at
        self.duration_seconds = duration_seconds
