"""
City Simulator — FastAPI application.

Agent-based city simulation and scenario management.

ROUTES:
  POST   /simulation/city/runs                — Create/start simulation run
  GET    /simulation/city/runs                — List runs
  GET    /simulation/city/runs/{id}           — Get run details
  PATCH  /simulation/city/runs/{id}           — Update run (pause/resume/stop)
  POST   /simulation/city/runs/{id}/agents    — Add agents to simulation
  GET    /simulation/city/runs/{id}/agents    — List agents in run
  POST   /simulation/city/runs/{id}/step      — Advance simulation by one tick
  GET    /simulation/city/runs/{id}/metrics   — Get simulation metrics/KPIs
  GET    /health                              — Health check (provided by create_app)
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
    description="Agent-based city simulation and scenario management",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/simulation/city/runs", response_model=schemas.RunResponse, status_code=201)
async def create_run(body: schemas.RunCreate):
    """Create/start a simulation run."""
    run = repository.repo.create_run(
        simulation_type=body.simulation_type,
        scenario=body.scenario,
        num_agents=body.num_agents,
    )
    return schemas.RunResponse(**run.to_dict())


@app.get("/simulation/city/runs", response_model=list[schemas.RunResponse])
async def list_runs():
    """List all simulation runs."""
    runs = repository.repo.list_runs()
    return [schemas.RunResponse(**r.to_dict()) for r in runs]


@app.get("/simulation/city/runs/{run_id}", response_model=schemas.RunResponse)
async def get_run(run_id: str):
    """Get run details."""
    run = repository.repo.get_run(run_id)
    if not run:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return schemas.RunResponse(**run.to_dict())


@app.patch("/simulation/city/runs/{run_id}", response_model=schemas.RunResponse)
async def update_run(run_id: str, body: schemas.RunUpdate):
    """Update run (pause/resume/stop)."""
    update_fields = body.model_dump(exclude_unset=True)
    run = repository.repo.update_run(run_id, **update_fields)
    if not run:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return schemas.RunResponse(**run.to_dict())


@app.post("/simulation/city/runs/{run_id}/agents", response_model=list[schemas.AgentResponse], status_code=201)
async def add_agents(run_id: str, body: schemas.AgentAdd):
    """Add agents to simulation."""
    run = repository.repo.get_run(run_id)
    if not run:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    agents = repository.repo.add_agents(run_id, body.agent_type, body.count)
    return [schemas.AgentResponse(**a.to_dict()) for a in agents]


@app.get("/simulation/city/runs/{run_id}/agents", response_model=list[schemas.AgentResponse])
async def list_agents(run_id: str):
    """List agents in a run."""
    run = repository.repo.get_run(run_id)
    if not run:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    agents = repository.repo.list_agents(run_id)
    return [schemas.AgentResponse(**a.to_dict()) for a in agents]


@app.post("/simulation/city/runs/{run_id}/step", response_model=schemas.StepResponse)
async def step_simulation(run_id: str):
    """Advance simulation by one tick."""
    result = repository.repo.step(run_id)
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found or not running")
    return schemas.StepResponse(**result)


@app.get("/simulation/city/runs/{run_id}/metrics", response_model=schemas.MetricsResponse)
async def get_metrics(run_id: str):
    """Get simulation metrics/KPIs."""
    metrics = repository.repo.get_metrics(run_id)
    if not metrics:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return schemas.MetricsResponse(**metrics.to_dict())
