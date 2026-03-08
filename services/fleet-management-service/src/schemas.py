"""
Pydantic request/response schemas for the fleet management service API.
"""

from typing import Optional, List, Dict

from pydantic import BaseModel, Field


# ── Response schemas ──

class FleetOverviewResponse(BaseModel):
    """GET /fleet/overview — high-level fleet statistics."""
    total_vehicles: int
    active_vehicles: int
    total_drivers: int
    active_drivers: int
    utilization_rate: float = Field(..., description="Percentage of fleet currently in use")


class FleetVehicleResponse(BaseModel):
    """Single vehicle in fleet listing."""
    id: str
    make: str
    model: str
    year: int
    license_plate: str
    status: str
    vehicle_type: str


class FleetVehicleListResponse(BaseModel):
    """GET /fleet/vehicles — fleet vehicle listing."""
    vehicles: List[FleetVehicleResponse]
    count: int


class FleetDriverResponse(BaseModel):
    """Single driver in fleet listing."""
    id: str
    full_name: str
    status: str
    rating: Optional[float] = None
    total_trips: int = 0


class FleetDriverListResponse(BaseModel):
    """GET /fleet/drivers — fleet driver listing."""
    drivers: List[FleetDriverResponse]
    count: int


class FleetUtilizationResponse(BaseModel):
    """GET /fleet/utilization — fleet utilization metrics."""
    period: str
    vehicle_utilization_pct: float
    driver_utilization_pct: float
    avg_trips_per_vehicle: float
    avg_trips_per_driver: float
