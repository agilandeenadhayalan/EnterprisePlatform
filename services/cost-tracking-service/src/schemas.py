"""
Pydantic request/response schemas for the cost tracking service API.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Request schemas ──

class AllocationCreate(BaseModel):
    """POST /costs/allocations — create an allocation rule."""
    service_name: str = Field(..., description="Service name")
    resource_type: str = Field(..., description="Resource type: compute, storage, network, database, cache")
    cost_per_unit: float = Field(..., description="Cost per unit")
    unit: str = Field(default="request", description="Unit of measurement")
    tags: Optional[dict[str, str]] = Field(default=None, description="Tags for categorization")
    period: str = Field(default="monthly", description="Billing period")


class CostRecordCreate(BaseModel):
    """POST /costs/record — record a cost event."""
    allocation_id: str = Field(..., description="Allocation rule ID")
    quantity: float = Field(..., description="Quantity consumed")
    trip_id: Optional[str] = Field(default=None, description="Associated trip ID")
    request_id: Optional[str] = Field(default=None, description="Associated request ID")


# ── Response schemas ──

class AllocationResponse(BaseModel):
    """A cost allocation rule."""
    id: str
    service_name: str
    resource_type: str
    cost_per_unit: float
    unit: str
    tags: dict[str, str] = {}
    period: str
    created_at: datetime


class CostRecordResponse(BaseModel):
    """A cost record."""
    id: str
    allocation_id: str
    quantity: float
    total_cost: float
    trip_id: Optional[str] = None
    request_id: Optional[str] = None
    recorded_at: datetime


class CostSummaryResponse(BaseModel):
    """Cost summary by service."""
    service_name: str
    total_cost: float
    breakdown_by_resource: dict[str, float]


class PerTripCostResponse(BaseModel):
    """Unit economics — cost per trip."""
    total_cost: float
    total_trips: int
    cost_per_trip: float
    breakdown: dict[str, float]
