"""
Chaos Experiment Service — FastAPI application.

Chaos engineering experiment management and steady state verification
for the observability platform.

ROUTES:
  GET  /chaos/experiments              — List experiments
  POST /chaos/experiments              — Create experiment
  GET  /chaos/experiments/{id}         — Get experiment
  POST /chaos/experiments/{id}/run     — Start a chaos run
  GET  /chaos/experiments/{id}/runs    — List runs for experiment
  GET  /chaos/experiments/{id}/blast-radius — Blast radius analysis
  POST /chaos/experiments/{id}/verify  — Verify steady state
  GET  /chaos/stats                    — Chaos experiment statistics
  GET  /health                         — Health check (provided by create_app)
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
    description="Chaos engineering experiment management and steady state verification for the observability platform",
    lifespan=lifespan,
)


# ── Routes ──


@app.get("/chaos/stats", response_model=schemas.ChaosStatsResponse)
async def chaos_stats():
    """Get chaos experiment statistics."""
    stats = repository.repo.get_stats()
    return schemas.ChaosStatsResponse(**stats)


@app.get("/chaos/experiments", response_model=schemas.ChaosExperimentListResponse)
async def list_experiments(
    type: Optional[str] = Query(default=None, alias="type", description="Filter by experiment type"),
    status: Optional[str] = Query(default=None, description="Filter by status"),
):
    """List all chaos experiments."""
    experiments = repository.repo.list_experiments()
    if type:
        experiments = [e for e in experiments if e.experiment_type == type]
    if status:
        experiments = [e for e in experiments if e.status == status]
    return schemas.ChaosExperimentListResponse(
        experiments=[schemas.ChaosExperimentResponse(**e.to_dict()) for e in experiments],
        total=len(experiments),
    )


@app.post("/chaos/experiments", response_model=schemas.ChaosExperimentResponse, status_code=201)
async def create_experiment(req: schemas.ChaosExperimentCreateRequest):
    """Create a new chaos experiment."""
    exp = repository.repo.create_experiment(req.model_dump())
    return schemas.ChaosExperimentResponse(**exp.to_dict())


@app.get("/chaos/experiments/{exp_id}", response_model=schemas.ChaosExperimentResponse)
async def get_experiment(exp_id: str):
    """Get a single experiment by ID."""
    exp = repository.repo.get_experiment(exp_id)
    if not exp:
        raise HTTPException(status_code=404, detail=f"Experiment '{exp_id}' not found")
    return schemas.ChaosExperimentResponse(**exp.to_dict())


@app.post("/chaos/experiments/{exp_id}/run", response_model=schemas.ChaosRunResponse, status_code=201)
async def start_run(exp_id: str):
    """Start a chaos run for an experiment."""
    exp = repository.repo.get_experiment(exp_id)
    if not exp:
        raise HTTPException(status_code=404, detail=f"Experiment '{exp_id}' not found")
    if exp.status == "draft":
        raise HTTPException(status_code=400, detail="Experiment must be approved before running")
    run = repository.repo.start_run(exp_id)
    return schemas.ChaosRunResponse(**run.to_dict())


@app.get("/chaos/experiments/{exp_id}/runs", response_model=schemas.ChaosRunListResponse)
async def list_runs(exp_id: str):
    """List runs for an experiment."""
    runs = repository.repo.list_runs_for_experiment(exp_id)
    return schemas.ChaosRunListResponse(
        runs=[schemas.ChaosRunResponse(**r.to_dict()) for r in runs],
        total=len(runs),
    )


@app.get("/chaos/experiments/{exp_id}/blast-radius", response_model=schemas.BlastRadiusResponse)
async def blast_radius(exp_id: str):
    """Get blast radius analysis for an experiment."""
    result = repository.repo.get_blast_radius(exp_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Experiment '{exp_id}' not found")
    return schemas.BlastRadiusResponse(**result)


@app.post("/chaos/experiments/{exp_id}/verify", response_model=schemas.VerificationResponse)
async def verify_steady_state(exp_id: str):
    """Verify steady state hypotheses against latest run."""
    result = repository.repo.verify_steady_state(exp_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Experiment '{exp_id}' not found")
    return schemas.VerificationResponse(**result)
