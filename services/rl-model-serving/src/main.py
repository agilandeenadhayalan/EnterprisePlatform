"""
RL Model Serving Service — FastAPI application.

RL model registry, serving, and comparison for production deployment.

ROUTES:
  POST /rl-models/predict          — Make prediction
  GET  /rl-models                  — List models
  GET  /rl-models/stats            — Model stats
  GET  /rl-models/{id}             — Get model
  POST /rl-models                  — Register model
  POST /rl-models/{id}/promote     — Promote to active
  POST /rl-models/{id}/retire      — Retire model
  POST /rl-models/compare          — Compare two models
  GET  /health                     — Health check
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
    description="RL model registry, serving, and comparison for production deployment",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/rl-models/predict", response_model=schemas.PredictionResponse)
async def predict(req: schemas.PredictRequest):
    """Make a prediction using a model."""
    pred = repository.repo.predict(req.model_id, req.state_input)
    if not pred:
        raise HTTPException(status_code=404, detail=f"Model '{req.model_id}' not found")
    return schemas.PredictionResponse(**pred.to_dict())


@app.post("/rl-models/compare", response_model=schemas.ComparisonResponse)
async def compare_models(req: schemas.CompareRequest):
    """Compare two models on a metric."""
    comparison = repository.repo.compare_models(req.model_a_id, req.model_b_id, req.metric)
    if not comparison:
        raise HTTPException(status_code=404, detail="One or both models not found")
    return schemas.ComparisonResponse(**comparison.to_dict())


@app.get("/rl-models/stats", response_model=schemas.ModelStatsResponse)
async def model_stats():
    """Get model statistics."""
    stats = repository.repo.get_stats()
    return schemas.ModelStatsResponse(**stats)


@app.get("/rl-models", response_model=schemas.RLModelListResponse)
async def list_models(
    status: Optional[str] = Query(default=None, description="Filter by status"),
    algorithm: Optional[str] = Query(default=None, description="Filter by algorithm"),
):
    """List all registered models."""
    models = repository.repo.list_models(status, algorithm)
    return schemas.RLModelListResponse(
        models=[schemas.RLModelResponse(**m.to_dict()) for m in models],
        total=len(models),
    )


@app.get("/rl-models/{model_id}", response_model=schemas.RLModelResponse)
async def get_model(model_id: str):
    """Get a specific model."""
    model = repository.repo.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")
    return schemas.RLModelResponse(**model.to_dict())


@app.post("/rl-models", response_model=schemas.RLModelResponse, status_code=201)
async def register_model(req: schemas.RegisterModelRequest):
    """Register a new model."""
    model = repository.repo.register_model(req.model_dump())
    return schemas.RLModelResponse(**model.to_dict())


@app.post("/rl-models/{model_id}/promote", response_model=schemas.RLModelResponse)
async def promote_model(model_id: str):
    """Promote a model to active status."""
    model = repository.repo.promote_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")
    return schemas.RLModelResponse(**model.to_dict())


@app.post("/rl-models/{model_id}/retire", response_model=schemas.RLModelResponse)
async def retire_model(model_id: str):
    """Retire a model."""
    model = repository.repo.retire_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")
    return schemas.RLModelResponse(**model.to_dict())
