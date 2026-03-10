"""
Traffic Simulator — FastAPI application.

Traffic patterns and congestion modeling.

ROUTES:
  POST   /simulation/traffic/runs                       — Start traffic simulation
  GET    /simulation/traffic/runs                       — List runs
  GET    /simulation/traffic/runs/{id}                  — Get run details
  POST   /simulation/traffic/runs/{id}/step             — Step simulation
  GET    /simulation/traffic/runs/{id}/congestion       — Get congestion map
  POST   /simulation/traffic/runs/{id}/incident         — Inject traffic incident
  GET    /simulation/traffic/runs/{id}/routes           — Get route conditions
  GET    /health                                        — Health check (provided by create_app)
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
    description="Traffic patterns and congestion modeling",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/simulation/traffic/runs", response_model=schemas.TrafficRunResponse, status_code=201)
async def create_run(body: schemas.TrafficRunCreate):
    """Start a traffic simulation run."""
    run = repository.repo.create_run(
        num_segments=body.num_segments,
        config=body.config,
    )
    return schemas.TrafficRunResponse(**run.to_dict())


@app.get("/simulation/traffic/runs", response_model=list[schemas.TrafficRunResponse])
async def list_runs():
    """List all traffic simulation runs."""
    runs = repository.repo.list_runs()
    return [schemas.TrafficRunResponse(**r.to_dict()) for r in runs]


@app.get("/simulation/traffic/runs/{run_id}", response_model=schemas.TrafficRunResponse)
async def get_run(run_id: str):
    """Get run details."""
    run = repository.repo.get_run(run_id)
    if not run:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return schemas.TrafficRunResponse(**run.to_dict())


@app.post("/simulation/traffic/runs/{run_id}/step", response_model=schemas.StepResponse)
async def step_simulation(run_id: str):
    """Step traffic simulation."""
    result = repository.repo.step(run_id)
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found or not running")
    return schemas.StepResponse(**result)


@app.get("/simulation/traffic/runs/{run_id}/congestion", response_model=list[schemas.CongestionMapEntry])
async def get_congestion(run_id: str):
    """Get congestion map."""
    congestion = repository.repo.get_congestion(run_id)
    if congestion is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return [schemas.CongestionMapEntry(**c) for c in congestion]


@app.post("/simulation/traffic/runs/{run_id}/incident", response_model=schemas.IncidentResponse, status_code=201)
async def inject_incident(run_id: str, body: schemas.IncidentInject):
    """Inject a traffic incident."""
    incident = repository.repo.inject_incident(
        run_id=run_id,
        segment_id=body.segment_id,
        incident_type=body.incident_type,
        severity=body.severity,
        impact_radius=body.impact_radius,
    )
    if not incident:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' or segment '{body.segment_id}' not found")
    return schemas.IncidentResponse(**incident.to_dict())


@app.get("/simulation/traffic/runs/{run_id}/routes", response_model=list[schemas.RouteConditionResponse])
async def get_routes(run_id: str):
    """Get route conditions."""
    conditions = repository.repo.get_route_conditions(run_id)
    if conditions is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return [schemas.RouteConditionResponse(**c) for c in conditions]
