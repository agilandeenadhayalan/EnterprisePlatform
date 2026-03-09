"""
Model Evaluation Service — FastAPI application.

Offline model evaluation and metrics computation. Runs evaluations on datasets,
compares models, and maintains a model leaderboard.

ROUTES:
  POST /evaluation/run             — Evaluate model on dataset
  GET  /evaluation/results         — List evaluation results
  GET  /evaluation/results/{id}    — Get evaluation details
  POST /evaluation/compare         — Compare two models
  GET  /evaluation/leaderboard     — Model leaderboard by metric
  GET  /health                     — Health check (provided by create_app)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import Query

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
    description="Offline model evaluation and metrics computation",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/evaluation/run", response_model=schemas.EvaluationResultResponse, status_code=201)
async def run_evaluation(request: schemas.EvaluationRunRequest):
    """Run an evaluation of a model on a dataset."""
    result = repository.repo.run_evaluation(
        model_name=request.model_name,
        model_version=request.model_version,
        dataset_id=request.dataset_id,
    )
    return schemas.EvaluationResultResponse(**result.to_dict())


@app.get("/evaluation/results", response_model=schemas.EvaluationResultListResponse)
async def list_results():
    """List all evaluation results."""
    results = repository.repo.list_results()
    return schemas.EvaluationResultListResponse(
        results=[schemas.EvaluationResultResponse(**r.to_dict()) for r in results],
        total=len(results),
    )


@app.get("/evaluation/results/{eval_id}", response_model=schemas.EvaluationResultResponse)
async def get_result(eval_id: str):
    """Get a specific evaluation result."""
    result = repository.repo.get_result(eval_id)
    if result is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Evaluation '{eval_id}' not found")
    return schemas.EvaluationResultResponse(**result.to_dict())


@app.post("/evaluation/compare", response_model=schemas.ModelComparisonResponse)
async def compare_models(request: schemas.CompareRequest):
    """Compare two models on the same dataset."""
    comparison = repository.repo.compare_models(
        model_a=request.model_a,
        model_b=request.model_b,
        dataset_id=request.dataset_id,
    )
    if comparison is None:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=404,
            detail="No evaluations found for one or both models on the specified dataset",
        )
    return schemas.ModelComparisonResponse(**comparison.to_dict())


@app.get("/evaluation/leaderboard", response_model=schemas.LeaderboardResponse)
async def leaderboard(
    metric: str = Query(default="rmse", description="Metric to rank by (rmse, mae, r2, mape)"),
    task: str = Query(default="regression", description="Task type filter"),
):
    """Get model leaderboard ranked by the specified metric."""
    entries = repository.repo.get_leaderboard(metric=metric, task=task)
    return schemas.LeaderboardResponse(
        entries=[schemas.LeaderboardEntry(**e) for e in entries],
        metric=metric,
        task=task,
        total=len(entries),
    )
