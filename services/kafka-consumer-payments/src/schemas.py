"""
Pydantic request/response schemas for the kafka-consumer-payments API.
"""

from typing import Optional

from pydantic import BaseModel, Field


# -- Request schemas --


class ProcessBatchRequest(BaseModel):
    """POST /process — batch of payment events to process."""

    events: list[dict] = Field(..., description="List of raw payment event dicts")


# -- Response schemas --


class ProcessedPaymentResponse(BaseModel):
    """Single processed payment result."""

    payment_id: str
    ride_id: str
    amount: float
    tip_amount: float
    total_amount: float
    payment_method: str
    status: str
    processed_at: str


class ProcessBatchResponse(BaseModel):
    """POST /process response."""

    processed: int
    failed: int
    clickhouse_written: int
    minio_archived: int
    results: list[ProcessedPaymentResponse]


class ProcessingStatsResponse(BaseModel):
    """GET /process/stats response."""

    events_processed: int
    events_failed: int
    clickhouse_writes: int
    minio_writes: int
    total_amount_processed: float
    last_processed_at: Optional[str] = None
    uptime_seconds: float
