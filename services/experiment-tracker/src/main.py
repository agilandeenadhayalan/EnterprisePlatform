"""
Experiment Tracker — FastAPI application.

MLflow experiment management proxy. Creates and manages experiments,
logs runs with params/metrics/artifacts, and compares metrics across runs.

ROUTES:
  POST /experiments                  — Create an experiment
  GET  /experiments                  — List experiments
  GET  /experiments/{id}             — Get experiment details
  GET  /experiments/{id}/runs        — List runs in an experiment
  POST /experiments/{id}/runs        — Log a new run
  GET  /experiments/{id}/compare     — Compare metrics across runs
  GET  /runs/{run_id}                — Get run details
  GET  /health                       — Health check (provided by create_app)
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
    description="MLflow experiment management proxy for tracking ML experiments and runs",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/experiments", response_model=schemas.ExperimentResponse, status_code=201)
async def create_experiment(body: schemas.ExperimentCreateRequest):
    """Create a new experiment."""
    exp = repository.repo.create_experiment(
        name=body.name,
        description=body.description,
    )
    return schemas.ExperimentResponse(**exp.to_dict())


@app.get("/experiments", response_model=schemas.ExperimentListResponse)
async def list_experiments():
    """List all experiments."""
    experiments = repository.repo.list_experiments()
    return schemas.ExperimentListResponse(
        experiments=[schemas.ExperimentResponse(**e.to_dict()) for e in experiments],
        total=len(experiments),
    )


@app.get("/experiments/{experiment_id}", response_model=schemas.ExperimentResponse)
async def get_experiment(experiment_id: str):
    """Get details for a specific experiment."""
    exp = repository.repo.get_experiment(experiment_id)
    if exp is None:
        raise HTTPException(status_code=404, detail=f"Experiment {experiment_id} not found")
    return schemas.ExperimentResponse(**exp.to_dict())


@app.get("/experiments/{experiment_id}/runs", response_model=schemas.RunListResponse)
async def list_runs(experiment_id: str):
    """List all runs in an experiment."""
    runs = repository.repo.list_runs(experiment_id)
    if runs is None:
        raise HTTPException(status_code=404, detail=f"Experiment {experiment_id} not found")
    return schemas.RunListResponse(
        runs=[schemas.RunResponse(**r.to_dict()) for r in runs],
        total=len(runs),
    )


@app.post("/experiments/{experiment_id}/runs", response_model=schemas.RunResponse, status_code=201)
async def create_run(experiment_id: str, body: schemas.RunCreateRequest):
    """Log a new run in an experiment."""
    run = repository.repo.create_run(
        experiment_id=experiment_id,
        run_name=body.run_name,
        params=body.params,
        metrics=body.metrics,
        artifacts=body.artifacts,
        status=body.status,
    )
    if run is None:
        raise HTTPException(status_code=404, detail=f"Experiment {experiment_id} not found")
    return schemas.RunResponse(**run.to_dict())


@app.get("/experiments/{experiment_id}/compare", response_model=schemas.CompareResponse)
async def compare_runs(experiment_id: str):
    """Compare metrics across all runs in an experiment."""
    comparisons = repository.repo.compare_metrics(experiment_id)
    if comparisons is None:
        raise HTTPException(status_code=404, detail=f"Experiment {experiment_id} not found")
    return schemas.CompareResponse(
        experiment_id=experiment_id,
        comparisons=[
            schemas.MetricComparisonResponse(
                metric_name=c.metric_name,
                runs=[schemas.MetricRunEntry(**r) for r in c.runs],
            )
            for c in comparisons
        ],
    )


@app.get("/runs/{run_id}", response_model=schemas.RunResponse)
async def get_run(run_id: str):
    """Get details for a specific run."""
    run = repository.repo.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return schemas.RunResponse(**run.to_dict())
