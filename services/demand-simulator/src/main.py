"""
Demand Simulator Service — FastAPI application.

Demand simulation with scenario management and event generation.

ROUTES:
  POST /simulator/scenarios             — Create scenario
  GET  /simulator/scenarios             — List scenarios
  GET  /simulator/scenarios/{id}        — Get scenario
  POST /simulator/run/{scenario_id}     — Run simulation
  GET  /simulator/runs                  — List runs
  GET  /simulator/runs/{id}             — Get run with events summary
  GET  /simulator/stats                 — Simulator statistics
  GET  /health                          — Health check (provided by create_app)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import Query, HTTPException

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
    description="Demand simulation with scenario management and event generation",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/simulator/scenarios", response_model=schemas.DemandScenarioResponse, status_code=201)
async def create_scenario(req: schemas.DemandScenarioCreateRequest):
    """Create a new demand scenario."""
    sc = repository.repo.create_scenario(req.model_dump())
    return schemas.DemandScenarioResponse(**sc.to_dict())


@app.get("/simulator/scenarios", response_model=schemas.DemandScenarioListResponse)
async def list_scenarios(
    pattern_type: Optional[str] = Query(default=None, description="Filter by pattern_type"),
):
    """List all demand scenarios."""
    scenarios = repository.repo.list_scenarios(pattern_type=pattern_type)
    return schemas.DemandScenarioListResponse(
        scenarios=[schemas.DemandScenarioResponse(**s.to_dict()) for s in scenarios],
        total=len(scenarios),
    )


@app.get("/simulator/scenarios/{sc_id}", response_model=schemas.DemandScenarioResponse)
async def get_scenario(sc_id: str):
    """Get a demand scenario by ID."""
    sc = repository.repo.get_scenario(sc_id)
    if not sc:
        raise HTTPException(status_code=404, detail=f"Scenario '{sc_id}' not found")
    return schemas.DemandScenarioResponse(**sc.to_dict())


@app.post("/simulator/run/{scenario_id}", response_model=schemas.SimulationRunResponse, status_code=201)
async def run_simulation(scenario_id: str):
    """Run a simulation for a scenario."""
    run = repository.repo.run_simulation(scenario_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found")
    return schemas.SimulationRunResponse(**run.to_dict())


@app.get("/simulator/runs", response_model=schemas.SimulationRunListResponse)
async def list_runs(
    status: Optional[str] = Query(default=None, description="Filter by status"),
):
    """List all simulation runs."""
    runs = repository.repo.list_runs(status=status)
    return schemas.SimulationRunListResponse(
        runs=[schemas.SimulationRunResponse(**r.to_dict()) for r in runs],
        total=len(runs),
    )


@app.get("/simulator/runs/{run_id}", response_model=schemas.SimulationRunResponse)
async def get_run(run_id: str):
    """Get a simulation run with events summary."""
    run = repository.repo.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return schemas.SimulationRunResponse(**run.to_dict())


@app.get("/simulator/stats", response_model=schemas.SimulatorStatsResponse)
async def simulator_stats():
    """Get simulator statistics."""
    stats = repository.repo.get_stats()
    return schemas.SimulatorStatsResponse(**stats)
