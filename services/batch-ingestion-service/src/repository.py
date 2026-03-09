"""
In-memory repository for Batch Ingestion Service.

Manages ingestion jobs, tracks file processing, and stores job
history for batch data ingestion into MinIO Bronze layer.
"""

import uuid
from datetime import datetime
from typing import Optional

from models import (
    IngestionJob,
    IngestionState,
    IngestionStats,
    KNOWN_SCHEMAS,
)


class IngestionRepository:
    def __init__(self):
        self._jobs: dict[str, IngestionJob] = {}

    def create_ingestion_job(
        self,
        schema_name: str,
        source: str,
        target_layer: str = "bronze",
    ) -> IngestionJob:
        job_id = str(uuid.uuid4())
        job = IngestionJob(
            job_id=job_id,
            schema_name=schema_name,
            source=source,
            target_layer=target_layer,
            state=IngestionState.VALIDATING,
            started_at=datetime.utcnow(),
        )
        self._jobs[job_id] = job
        return job

    def complete_job(
        self,
        job_id: str,
        files_processed: int,
        total_bytes: int,
        total_rows: int,
        minio_path: str,
    ) -> Optional[IngestionJob]:
        job = self._jobs.get(job_id)
        if not job:
            return None
        job.state = IngestionState.COMPLETED
        job.stats = IngestionStats(
            files_processed=files_processed,
            total_bytes=total_bytes,
            total_rows=total_rows,
        )
        job.minio_path = minio_path
        job.event_produced = True
        job.completed_at = datetime.utcnow()
        return job

    def fail_job(self, job_id: str, error_message: str) -> Optional[IngestionJob]:
        job = self._jobs.get(job_id)
        if not job:
            return None
        job.state = IngestionState.FAILED
        job.error_message = error_message
        job.completed_at = datetime.utcnow()
        return job

    def get_job(self, job_id: str) -> Optional[IngestionJob]:
        return self._jobs.get(job_id)

    def get_all_jobs(self) -> list[IngestionJob]:
        return list(self._jobs.values())

    def get_jobs_by_state(self, state: IngestionState) -> list[IngestionJob]:
        return [j for j in self._jobs.values() if j.state == state]

    def schema_exists(self, schema_name: str) -> bool:
        return schema_name in KNOWN_SCHEMAS

    def get_all_schemas(self) -> list[dict]:
        return list(KNOWN_SCHEMAS.values())

    def validate_schema(self, schema_name: str, file_format: str) -> tuple[bool, str]:
        if schema_name not in KNOWN_SCHEMAS:
            return False, f"Unknown schema: {schema_name}"
        schema = KNOWN_SCHEMAS[schema_name]
        if file_format not in schema["formats"]:
            return False, f"Format '{file_format}' not supported for schema '{schema_name}'. Supported: {schema['formats']}"
        return True, ""


# Singleton
ingestion_repo = IngestionRepository()
