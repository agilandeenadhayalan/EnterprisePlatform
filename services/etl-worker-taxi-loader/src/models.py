"""
Domain models for ETL Worker Taxi Loader service.

Represents NYC taxi trip data loading jobs, checkpoints for resumable
loads, and the taxi record structure mapped to ClickHouse fact_rides.
"""

from datetime import datetime
from enum import Enum
from typing import Optional


class LoadState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class LoadJob:
    def __init__(
        self,
        job_id: str,
        year: int,
        month: int,
        state: LoadState = LoadState.PENDING,
        rows_loaded: int = 0,
        total_rows: Optional[int] = None,
        current_file: Optional[str] = None,
        speed_rows_per_sec: float = 0.0,
        error_message: Optional[str] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
    ):
        self.job_id = job_id
        self.year = year
        self.month = month
        self.state = state
        self.rows_loaded = rows_loaded
        self.total_rows = total_rows
        self.current_file = current_file
        self.speed_rows_per_sec = speed_rows_per_sec
        self.error_message = error_message
        self.started_at = started_at or datetime.utcnow()
        self.completed_at = completed_at


class LoadStatus:
    def __init__(
        self,
        job_id: str,
        rows_loaded: int = 0,
        total_rows: Optional[int] = None,
        current_file: Optional[str] = None,
        speed_rows_per_sec: float = 0.0,
        percent_complete: float = 0.0,
    ):
        self.job_id = job_id
        self.rows_loaded = rows_loaded
        self.total_rows = total_rows
        self.current_file = current_file
        self.speed_rows_per_sec = speed_rows_per_sec
        self.percent_complete = percent_complete


class LoadCheckpoint:
    def __init__(
        self,
        year: int,
        month: int,
        last_row_offset: int = 0,
        last_file: Optional[str] = None,
        rows_loaded: int = 0,
        updated_at: Optional[datetime] = None,
    ):
        self.year = year
        self.month = month
        self.last_row_offset = last_row_offset
        self.last_file = last_file
        self.rows_loaded = rows_loaded
        self.updated_at = updated_at or datetime.utcnow()


class TaxiRecord:
    """Represents a single NYC taxi trip record mapped to fact_rides schema."""

    COLUMN_MAPPING = {
        "VendorID": "vendor_id",
        "tpep_pickup_datetime": "pickup_datetime",
        "tpep_dropoff_datetime": "dropoff_datetime",
        "passenger_count": "passenger_count",
        "trip_distance": "trip_distance",
        "PULocationID": "pickup_location_id",
        "DOLocationID": "dropoff_location_id",
        "payment_type": "payment_type",
        "fare_amount": "fare_amount",
        "tip_amount": "tip_amount",
        "total_amount": "total_amount",
    }

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
