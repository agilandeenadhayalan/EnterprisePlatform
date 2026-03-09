"""
Data models for kafka-consumer-payments.

PaymentEvent: raw payment event from Kafka.
PaymentFact: transformed record for ClickHouse fact_payments.
ProcessingStats: dual-write processing statistics.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PaymentEvent(BaseModel):
    """Raw payment event consumed from Kafka."""

    event_id: str = Field(..., description="Unique event identifier")
    payment_id: str = Field(..., description="Payment identifier")
    ride_id: str = Field(..., description="Associated ride identifier")
    rider_id: str = Field(..., description="Rider identifier")
    driver_id: str = Field(..., description="Driver identifier")
    amount: float = Field(..., description="Payment amount in USD")
    tip_amount: float = Field(0.0, description="Tip amount in USD")
    payment_method: str = Field("card", description="Payment method (card/cash/wallet)")
    currency: str = Field("USD", description="Currency code")
    status: str = Field("completed", description="Payment status")
    processor: str = Field("stripe", description="Payment processor")
    timestamp: str = Field(..., description="Payment timestamp ISO string")


class PaymentFact(BaseModel):
    """Transformed payment record for ClickHouse fact_payments."""

    payment_id: str
    ride_id: str
    rider_id: str
    driver_id: str
    amount: float
    tip_amount: float
    total_amount: float
    payment_method: str
    currency: str
    status: str
    processor: str
    payment_at: datetime
    processed_at: datetime


class ProcessingStats(BaseModel):
    """Dual-write processing statistics."""

    events_processed: int = 0
    events_failed: int = 0
    clickhouse_writes: int = 0
    minio_writes: int = 0
    total_amount_processed: float = 0.0
    last_processed_at: Optional[str] = None
    uptime_seconds: float = 0.0
