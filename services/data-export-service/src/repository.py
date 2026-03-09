"""
Data export repository — in-memory export job tracking.

Tracks export jobs and simulates async export completion. In production,
this would write to MinIO and track jobs in PostgreSQL.
"""

import uuid
import random
from datetime import datetime
from typing import Optional

from models import ExportJob, ExportFormat


# Supported export formats
EXPORT_FORMATS = [
    ExportFormat(
        format_id="csv",
        name="CSV",
        description="Comma-separated values — compatible with Excel, Google Sheets, and most data tools",
        content_type="text/csv",
        extension=".csv",
    ),
    ExportFormat(
        format_id="parquet",
        name="Apache Parquet",
        description="Columnar storage format — efficient for analytics workloads, preserves data types",
        content_type="application/octet-stream",
        extension=".parquet",
    ),
    ExportFormat(
        format_id="json",
        name="JSON",
        description="JavaScript Object Notation — human-readable, suitable for API integrations",
        content_type="application/json",
        extension=".json",
    ),
    ExportFormat(
        format_id="xlsx",
        name="Excel (XLSX)",
        description="Microsoft Excel spreadsheet — supports multiple sheets and formatting",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        extension=".xlsx",
    ),
]

VALID_FORMAT_IDS = {f.format_id for f in EXPORT_FORMATS}


class ExportRepository:
    """In-memory export job tracking."""

    def __init__(self):
        self._jobs: dict[str, ExportJob] = {}
        self._rng = random.Random(42)

    def get_formats(self) -> list[ExportFormat]:
        """Get all supported export formats."""
        return EXPORT_FORMATS

    def create_job(
        self,
        query: str,
        format: str,
        destination: str = "download",
    ) -> ExportJob:
        """Start a new export job (mock: completes immediately with simulated data)."""
        job_id = str(uuid.uuid4())
        row_count = self._rng.randint(100, 100000)

        # Simulate file size based on format and row count
        bytes_per_row = {"csv": 150, "json": 250, "parquet": 50, "xlsx": 200}
        file_size = row_count * bytes_per_row.get(format, 150)

        # Generate mock download URL
        extension = {"csv": ".csv", "parquet": ".parquet", "json": ".json", "xlsx": ".xlsx"}
        download_url = f"https://storage.mobility-platform.io/exports/{job_id}{extension.get(format, '.csv')}"

        job = ExportJob(
            id=job_id,
            query=query,
            format=format,
            destination=destination,
            status="completed",
            row_count=row_count,
            file_size_bytes=file_size,
            download_url=download_url,
            completed_at=datetime.utcnow(),
        )
        self._jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> Optional[ExportJob]:
        """Get an export job by ID."""
        return self._jobs.get(job_id)

    def list_jobs(self) -> list[ExportJob]:
        """List all export jobs, newest first."""
        return sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)

    def delete_job(self, job_id: str) -> bool:
        """Cancel or delete an export job."""
        if job_id in self._jobs:
            del self._jobs[job_id]
            return True
        return False


# Singleton repository instance
repo = ExportRepository()
