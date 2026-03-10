"""
Cost Tracking repository — in-memory cost allocation and record storage.

Manages cost allocations, records, summaries, and unit economics.
"""

import uuid
from typing import Optional

from models import CostAllocation, CostRecord


class CostTrackingRepository:
    """In-memory cost tracking storage."""

    def __init__(self):
        self._allocations: dict[str, CostAllocation] = {}
        self._records: list[CostRecord] = []

    # ── Allocations ──

    def create_allocation(
        self,
        service_name: str,
        resource_type: str,
        cost_per_unit: float,
        unit: str = "request",
        tags: Optional[dict[str, str]] = None,
        period: str = "monthly",
    ) -> CostAllocation:
        """Create an allocation rule."""
        alloc_id = str(uuid.uuid4())
        alloc = CostAllocation(
            id=alloc_id,
            service_name=service_name,
            resource_type=resource_type,
            cost_per_unit=cost_per_unit,
            unit=unit,
            tags=tags,
            period=period,
        )
        self._allocations[alloc_id] = alloc
        return alloc

    def get_allocation(self, alloc_id: str) -> Optional[CostAllocation]:
        """Get an allocation by ID."""
        return self._allocations.get(alloc_id)

    def list_allocations(self) -> list[CostAllocation]:
        """List all allocations."""
        return list(self._allocations.values())

    # ── Cost records ──

    def record_cost(
        self,
        allocation_id: str,
        quantity: float,
        trip_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> Optional[CostRecord]:
        """Record a cost event."""
        alloc = self._allocations.get(allocation_id)
        if not alloc:
            return None
        record_id = str(uuid.uuid4())
        total_cost = alloc.cost_per_unit * quantity
        record = CostRecord(
            id=record_id,
            allocation_id=allocation_id,
            quantity=quantity,
            total_cost=round(total_cost, 4),
            trip_id=trip_id,
            request_id=request_id,
        )
        self._records.append(record)
        return record

    def list_records(
        self,
        service: Optional[str] = None,
    ) -> list[CostRecord]:
        """List cost records with optional filters."""
        if service:
            alloc_ids = {a.id for a in self._allocations.values() if a.service_name == service}
            return [r for r in self._records if r.allocation_id in alloc_ids]
        return list(self._records)

    # ── Summary ──

    def get_summary(self) -> list[dict]:
        """Get cost summary by service/resource."""
        # Group costs by service
        service_costs: dict[str, dict[str, float]] = {}
        for record in self._records:
            alloc = self._allocations.get(record.allocation_id)
            if not alloc:
                continue
            svc = alloc.service_name
            res = alloc.resource_type
            if svc not in service_costs:
                service_costs[svc] = {}
            service_costs[svc][res] = service_costs[svc].get(res, 0) + record.total_cost

        return [
            {
                "service_name": svc,
                "total_cost": round(sum(breakdown.values()), 4),
                "breakdown_by_resource": {k: round(v, 4) for k, v in breakdown.items()},
            }
            for svc, breakdown in service_costs.items()
        ]

    # ── Per-trip cost ──

    def get_per_trip_cost(self) -> dict:
        """Calculate unit economics (cost per trip)."""
        trip_records = [r for r in self._records if r.trip_id]
        if not trip_records:
            return {
                "total_cost": 0.0,
                "total_trips": 0,
                "cost_per_trip": 0.0,
                "breakdown": {},
            }

        unique_trips = set(r.trip_id for r in trip_records)
        total_cost = sum(r.total_cost for r in trip_records)

        breakdown: dict[str, float] = {}
        for record in trip_records:
            alloc = self._allocations.get(record.allocation_id)
            if alloc:
                res = alloc.resource_type
                breakdown[res] = breakdown.get(res, 0) + record.total_cost

        num_trips = len(unique_trips)
        return {
            "total_cost": round(total_cost, 4),
            "total_trips": num_trips,
            "cost_per_trip": round(total_cost / num_trips, 4) if num_trips else 0.0,
            "breakdown": {k: round(v, 4) for k, v in breakdown.items()},
        }


# Singleton repository instance
repo = CostTrackingRepository()
