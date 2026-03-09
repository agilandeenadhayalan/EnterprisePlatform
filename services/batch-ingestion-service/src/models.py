"""
Domain models for Batch Ingestion Service.

Represents ingestion jobs, file metadata, known data schemas,
and ingestion statistics for Bronze layer data lake storage.
"""

from datetime import datetime
from enum import Enum
from typing import Optional


class IngestionState(str, Enum):
    PENDING = "pending"
    VALIDATING = "validating"
    INGESTING = "ingesting"
    COMPLETED = "completed"
    FAILED = "failed"


class FileFormat(str, Enum):
    CSV = "csv"
    PARQUET = "parquet"
    JSON = "json"
    AVRO = "avro"


class FileMetadata:
    def __init__(
        self,
        filename: str,
        format: FileFormat,
        size_bytes: int,
        row_count: Optional[int] = None,
        schema_name: Optional[str] = None,
        source: Optional[str] = None,
    ):
        self.filename = filename
        self.format = format
        self.size_bytes = size_bytes
        self.row_count = row_count
        self.schema_name = schema_name
        self.source = source


class IngestionRequest:
    def __init__(
        self,
        schema_name: str,
        source: str,
        files: list[FileMetadata],
        target_layer: str = "bronze",
    ):
        self.schema_name = schema_name
        self.source = source
        self.files = files
        self.target_layer = target_layer


class IngestionStats:
    def __init__(
        self,
        files_processed: int = 0,
        total_bytes: int = 0,
        total_rows: int = 0,
        failed_files: int = 0,
    ):
        self.files_processed = files_processed
        self.total_bytes = total_bytes
        self.total_rows = total_rows
        self.failed_files = failed_files


class IngestionJob:
    def __init__(
        self,
        job_id: str,
        schema_name: str,
        source: str,
        target_layer: str = "bronze",
        state: IngestionState = IngestionState.PENDING,
        stats: Optional[IngestionStats] = None,
        minio_path: Optional[str] = None,
        event_produced: bool = False,
        error_message: Optional[str] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
    ):
        self.job_id = job_id
        self.schema_name = schema_name
        self.source = source
        self.target_layer = target_layer
        self.state = state
        self.stats = stats or IngestionStats()
        self.minio_path = minio_path
        self.event_produced = event_produced
        self.error_message = error_message
        self.started_at = started_at or datetime.utcnow()
        self.completed_at = completed_at


# Known data schemas for validation
KNOWN_SCHEMAS = {
    "taxi_trips": {
        "name": "taxi_trips",
        "description": "NYC Yellow Taxi Trip Records",
        "required_columns": ["VendorID", "tpep_pickup_datetime", "tpep_dropoff_datetime", "passenger_count", "trip_distance", "total_amount"],
        "formats": ["parquet", "csv"],
    },
    "weather_observations": {
        "name": "weather_observations",
        "description": "NOAA Weather Station Observations",
        "required_columns": ["station_id", "observation_date", "temperature", "precipitation"],
        "formats": ["csv", "json"],
    },
    "ride_events": {
        "name": "ride_events",
        "description": "Platform Ride Event Streams",
        "required_columns": ["event_id", "ride_id", "event_type", "timestamp"],
        "formats": ["json", "avro"],
    },
    "driver_locations": {
        "name": "driver_locations",
        "description": "Driver GPS Location Updates",
        "required_columns": ["driver_id", "latitude", "longitude", "timestamp"],
        "formats": ["json", "parquet"],
    },
    "payment_transactions": {
        "name": "payment_transactions",
        "description": "Payment Processing Records",
        "required_columns": ["transaction_id", "ride_id", "amount", "payment_method", "timestamp"],
        "formats": ["json", "csv"],
    },
}
