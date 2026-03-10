"""
Experiment Service — FastAPI application.

Experiment lifecycle management for A/B tests, feature flags, MAB, and MVT experiments.

ROUTES:
  POST /experiments                  — Create experiment
  GET  /experiments                  — List experiments
  GET  /experiments/stats            — Experiment statistics
  GET  /experiments/{id}             — Get experiment
  PUT  /experiments/{id}             — Update experiment
  POST /experiments/{id}/start       — Start experiment
  POST /experiments/{id}/pause       — Pause experiment
  POST /experiments/{id}/complete    — Complete experiment
  DELETE /experiments/{id}           — Archive experiment
  GET  /health                       — Health check
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
    description="Experiment lifecycle management for A/B tests, feature flags, MAB, and MVT experiments",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/experiments", response_model=schemas.ExperimentResponse, status_code=201)
async def create_experiment(req: schemas.ExperimentCreateRequest):
    """Create a new experiment."""
    exp = repository.repo.create_experiment(req.model_dump())
    return schemas.ExperimentResponse(**exp.to_dict())


@app.get("/experiments/stats", response_model=schemas.ExperimentStatsResponse)
async def experiment_stats():
    """Get experiment statistics."""
    stats = repository.repo.get_stats()
    return schemas.ExperimentStatsResponse(**stats)


@app.get("/experiments", response_model=schemas.ExperimentListResponse)
async def list_experiments(
    status: Optional[str] = Query(default=None, description="Filter by status"),
    experiment_type: Optional[str] = Query(default=None, description="Filter by experiment type"),
):
    """List all experiments."""
    experiments = repository.repo.list_experiments()
    if status:
        experiments = [e for e in experiments if e.status == status]
    if experiment_type:
        experiments = [e for e in experiments if e.experiment_type == experiment_type]
    return schemas.ExperimentListResponse(
        experiments=[schemas.ExperimentResponse(**e.to_dict()) for e in experiments],
        total=len(experiments),
    )


@app.get("/experiments/{experiment_id}", response_model=schemas.ExperimentResponse)
async def get_experiment(experiment_id: str):
    """Get a single experiment by ID."""
    exp = repository.repo.get_experiment(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found")
    return schemas.ExperimentResponse(**exp.to_dict())


@app.put("/experiments/{experiment_id}", response_model=schemas.ExperimentResponse)
async def update_experiment(experiment_id: str, req: schemas.ExperimentUpdateRequest):
    """Update an experiment."""
    exp = repository.repo.update_experiment(experiment_id, req.model_dump(exclude_unset=True))
    if not exp:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found")
    return schemas.ExperimentResponse(**exp.to_dict())


@app.post("/experiments/{experiment_id}/start", response_model=schemas.ExperimentResponse)
async def start_experiment(experiment_id: str):
    """Start an experiment (must be draft or paused)."""
    result = repository.repo.start_experiment(experiment_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found")
    if result == "invalid_status":
        raise HTTPException(status_code=400, detail="Experiment must be in draft or paused status to start")
    return schemas.ExperimentResponse(**result.to_dict())


@app.post("/experiments/{experiment_id}/pause", response_model=schemas.ExperimentResponse)
async def pause_experiment(experiment_id: str):
    """Pause a running experiment."""
    result = repository.repo.pause_experiment(experiment_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found")
    if result == "invalid_status":
        raise HTTPException(status_code=400, detail="Experiment must be running to pause")
    return schemas.ExperimentResponse(**result.to_dict())


@app.post("/experiments/{experiment_id}/complete", response_model=schemas.ExperimentResponse)
async def complete_experiment(experiment_id: str):
    """Complete a running experiment."""
    result = repository.repo.complete_experiment(experiment_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found")
    if result == "invalid_status":
        raise HTTPException(status_code=400, detail="Experiment must be running to complete")
    return schemas.ExperimentResponse(**result.to_dict())


@app.delete("/experiments/{experiment_id}", response_model=schemas.ExperimentResponse)
async def archive_experiment(experiment_id: str):
    """Archive an experiment."""
    exp = repository.repo.archive_experiment(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found")
    return schemas.ExperimentResponse(**exp.to_dict())
