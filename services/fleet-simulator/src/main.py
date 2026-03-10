"""
Fleet Simulator — FastAPI application.

Fleet behavior simulation and driver patterns.

ROUTES:
  POST   /simulation/fleet/runs                     — Start fleet simulation
  GET    /simulation/fleet/runs                     — List runs
  GET    /simulation/fleet/runs/{id}                — Get run details
  POST   /simulation/fleet/runs/{id}/step           — Step simulation
  GET    /simulation/fleet/runs/{id}/drivers        — Get driver states
  POST   /simulation/fleet/runs/{id}/demand         — Inject demand event
  GET    /simulation/fleet/runs/{id}/supply-demand  — Supply/demand analytics
  GET    /health                                    — Health check (provided by create_app)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mobility_common.fastapi.app import create_app

import config as service_config
import schemas
import repository


@asynccontextmanager
async def lifespan(app):
    yield


app = create_app(
    title=service_config.settings.service_name,
    version="0.1.0",
    description="Fleet behavior simulation and driver patterns",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/simulation/fleet/runs", response_model=schemas.FleetRunResponse, status_code=201)
async def create_run(body: schemas.FleetRunCreate):
    """Start a fleet simulation run."""
    run = repository.repo.create_run(
        num_drivers=body.num_drivers,
        config=body.config,
    )
    return schemas.FleetRunResponse(**run.to_dict())


@app.get("/simulation/fleet/runs", response_model=list[schemas.FleetRunResponse])
async def list_runs():
    """List all fleet simulation runs."""
    runs = repository.repo.list_runs()
    return [schemas.FleetRunResponse(**r.to_dict()) for r in runs]


@app.get("/simulation/fleet/runs/{run_id}", response_model=schemas.FleetRunResponse)
async def get_run(run_id: str):
    """Get run details."""
    run = repository.repo.get_run(run_id)
    if not run:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return schemas.FleetRunResponse(**run.to_dict())


@app.post("/simulation/fleet/runs/{run_id}/step", response_model=schemas.StepResponse)
async def step_simulation(run_id: str):
    """Step fleet simulation."""
    result = repository.repo.step(run_id)
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found or not running")
    return schemas.StepResponse(**result)


@app.get("/simulation/fleet/runs/{run_id}/drivers", response_model=list[schemas.DriverResponse])
async def get_drivers(run_id: str):
    """Get driver states."""
    run = repository.repo.get_run(run_id)
    if not run:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    drivers = repository.repo.get_drivers(run_id)
    return [schemas.DriverResponse(**d.to_dict()) for d in drivers]


@app.post("/simulation/fleet/runs/{run_id}/demand", response_model=schemas.DemandEventResponse, status_code=201)
async def inject_demand(run_id: str, body: schemas.DemandInject):
    """Inject a demand event."""
    event = repository.repo.inject_demand(
        run_id=run_id,
        pickup=body.pickup,
        dropoff=body.dropoff,
    )
    if not event:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return schemas.DemandEventResponse(**event.to_dict())


@app.get("/simulation/fleet/runs/{run_id}/supply-demand", response_model=schemas.SupplyDemandResponse)
async def supply_demand(run_id: str):
    """Supply/demand analytics."""
    result = repository.repo.get_supply_demand(run_id)
    if result is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return schemas.SupplyDemandResponse(**result)
