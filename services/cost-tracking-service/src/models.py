"""
Domain models for the cost tracking service.

Tracks cost per trip/request and resource allocation.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional


class ResourceType(str, Enum):
    """Types of resources that incur costs."""
    COMPUTE = "compute"
    STORAGE = "storage"
    NETWORK = "network"
    DATABASE = "database"
    CACHE = "cache"


class CostAllocation:
    """A cost allocation rule for a service/resource."""

    def __init__(
        self,
        id: str,
        service_name: str,
        resource_type: str,
        cost_per_unit: float,
        unit: str = "request",
        tags: Optional[dict[str, str]] = None,
        period: str = "monthly",
        created_at: Optional[datetime] = None,
    ):
        self.id = id
        self.service_name = service_name
        self.resource_type = resource_type
        self.cost_per_unit = cost_per_unit
        self.unit = unit
        self.tags = tags or {}
        self.period = period
        self.created_at = created_at or datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "service_name": self.service_name,
            "resource_type": self.resource_type,
            "cost_per_unit": self.cost_per_unit,
            "unit": self.unit,
            "tags": self.tags,
            "period": self.period,
            "created_at": self.created_at.isoformat(),
        }


class CostRecord:
    """A cost event record."""

    def __init__(
        self,
        id: str,
        allocation_id: str,
        quantity: float,
        total_cost: float,
        trip_id: Optional[str] = None,
        request_id: Optional[str] = None,
        recorded_at: Optional[datetime] = None,
    ):
        self.id = id
        self.allocation_id = allocation_id
        self.quantity = quantity
        self.total_cost = total_cost
        self.trip_id = trip_id
        self.request_id = request_id
        self.recorded_at = recorded_at or datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "allocation_id": self.allocation_id,
            "quantity": self.quantity,
            "total_cost": self.total_cost,
            "trip_id": self.trip_id,
            "request_id": self.request_id,
            "recorded_at": self.recorded_at.isoformat(),
        }
