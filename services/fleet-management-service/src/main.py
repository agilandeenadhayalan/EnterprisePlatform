"""
Fleet Management Service — FastAPI application.

ROUTES:
  GET /fleet/overview     — High-level fleet statistics
  GET /fleet/vehicles     — List all fleet vehicles
  GET /fleet/drivers      — List all fleet drivers
  GET /fleet/utilization  — Fleet utilization metrics
  GET /health             — Health check (provided by create_app)
"""

import sys
from pathlib import Path

# Add project root for mobility-common imports
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
# Add service src for local imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mobility_common.fastapi.app import create_app

import config as service_config
import schemas
import repository


app = create_app(
    title="Fleet Management Service",
    version="0.1.0",
    description="Fleet overview and management for Smart Mobility Platform",
)

fleet_repo = repository.FleetRepository()


# ── Routes ──


@app.get("/fleet/overview", response_model=schemas.FleetOverviewResponse)
async def fleet_overview():
    """Get high-level fleet statistics."""
    data = await fleet_repo.get_overview()
    return schemas.FleetOverviewResponse(**data)


@app.get("/fleet/vehicles", response_model=schemas.FleetVehicleListResponse)
async def fleet_vehicles():
    """List all fleet vehicles."""
    vehicles = await fleet_repo.get_vehicles()
    return schemas.FleetVehicleListResponse(
        vehicles=[schemas.FleetVehicleResponse(**v) for v in vehicles],
        count=len(vehicles),
    )


@app.get("/fleet/drivers", response_model=schemas.FleetDriverListResponse)
async def fleet_drivers():
    """List all fleet drivers."""
    drivers = await fleet_repo.get_drivers()
    return schemas.FleetDriverListResponse(
        drivers=[schemas.FleetDriverResponse(**d) for d in drivers],
        count=len(drivers),
    )


@app.get("/fleet/utilization", response_model=schemas.FleetUtilizationResponse)
async def fleet_utilization():
    """Get fleet utilization metrics."""
    data = await fleet_repo.get_utilization()
    return schemas.FleetUtilizationResponse(**data)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=service_config.settings.service_port,
        reload=service_config.settings.debug,
    )
