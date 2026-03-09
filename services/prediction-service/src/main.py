"""
Prediction Service — FastAPI application.

Real-time REST inference endpoint for ML models. Supports single and batch
predictions, model loading/reloading, and latency tracking.

ROUTES:
  POST /predict                    — Single prediction
  POST /predict/batch              — Batch predictions
  GET  /predict/models             — List loaded models
  POST /predict/models/{name}/load — Load/reload a model
  GET  /predict/models/{name}/info — Model metadata + perf stats
  GET  /predict/latency            — Inference latency statistics
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
    description="Real-time REST inference endpoint for ML models",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/predict", response_model=schemas.PredictionResponse)
async def predict(request: schemas.PredictionRequest):
    """Run a single prediction with the specified model."""
    try:
        result = repository.repo.predict(request.model_name, request.features)
    except KeyError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=str(exc))
    return schemas.PredictionResponse(**result.to_dict())


@app.post("/predict/batch", response_model=schemas.BatchPredictionResponse)
async def predict_batch(request: schemas.BatchPredictionRequest):
    """Run batch predictions with the specified model."""
    try:
        results = repository.repo.predict_batch(request.model_name, request.instances)
    except KeyError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=str(exc))
    predictions = [schemas.PredictionResponse(**r.to_dict()) for r in results]
    avg_latency = round(sum(p.latency_ms for p in predictions) / len(predictions), 3) if predictions else 0.0
    return schemas.BatchPredictionResponse(
        predictions=predictions,
        total=len(predictions),
        avg_latency_ms=avg_latency,
    )


@app.get("/predict/models", response_model=schemas.LoadedModelListResponse)
async def list_models():
    """List all loaded models."""
    models = repository.repo.list_models()
    return schemas.LoadedModelListResponse(
        models=[schemas.LoadedModelResponse(**m.to_dict()) for m in models],
        total=len(models),
    )


@app.post("/predict/models/{name}/load", response_model=schemas.LoadedModelResponse)
async def load_model(name: str, request: schemas.ModelLoadRequest = None):
    """Load or reload a model by name."""
    if request is None:
        request = schemas.ModelLoadRequest()
    model = repository.repo.load_model(name, version=request.version)
    return schemas.LoadedModelResponse(**model.to_dict())


@app.get("/predict/models/{name}/info", response_model=schemas.LoadedModelResponse)
async def model_info(name: str):
    """Get model metadata and performance statistics."""
    model = repository.repo.get_model(name)
    if model is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Model '{name}' is not loaded")
    return schemas.LoadedModelResponse(**model.to_dict())


@app.get("/predict/latency", response_model=schemas.LatencyStatsResponse)
async def latency_stats():
    """Get inference latency statistics across all models."""
    stats = repository.repo.get_latency_stats()
    return schemas.LatencyStatsResponse(
        models=[schemas.LoadedModelResponse(**m.to_dict()) for m in stats["models"]],
        overall_avg_latency_ms=stats["overall_avg_latency_ms"],
        total_requests=stats["total_requests"],
    )
