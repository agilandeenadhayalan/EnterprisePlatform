"""
Prediction Logger — FastAPI application.

Prediction logging for ML model observability.
Logs individual and batch predictions with features, confidence,
and latency. Provides query and statistics endpoints.

ROUTES:
  POST /predictions/log         — Log a prediction
  POST /predictions/log/batch   — Log batch of predictions
  GET  /predictions/log         — Query prediction log
  GET  /predictions/log/stats   — Prediction volume statistics
  GET  /predictions/log/{id}    — Get a specific logged prediction
  GET  /health                  — Health check (provided by create_app)
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
    description="Prediction logging for ML model observability",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/predictions/log", response_model=schemas.PredictionLogCreateResponse, status_code=201)
async def log_prediction(req: schemas.PredictionLogRequest):
    """Log a single prediction."""
    log_entry = repository.repo.log_prediction(req.model_dump())
    return schemas.PredictionLogCreateResponse(id=log_entry.id, message="Prediction logged")


@app.post("/predictions/log/batch", response_model=schemas.PredictionLogBatchResponse, status_code=201)
async def log_batch(req: schemas.PredictionLogBatchRequest):
    """Log a batch of predictions."""
    items = [p.model_dump() for p in req.predictions]
    count = repository.repo.log_batch(items)
    return schemas.PredictionLogBatchResponse(logged=count, message=f"Logged {count} predictions")


@app.get("/predictions/log", response_model=schemas.PredictionLogListResponse)
async def query_logs(
    model: Optional[str] = Query(default=None, description="Filter by model name"),
    date_from: Optional[str] = Query(default=None, description="Start date (ISO)"),
    date_to: Optional[str] = Query(default=None, description="End date (ISO)"),
    limit: int = Query(default=50, description="Max results"),
):
    """Query prediction log."""
    logs = repository.repo.query_logs(model=model, date_from=date_from, date_to=date_to, limit=limit)
    return schemas.PredictionLogListResponse(
        predictions=[schemas.PredictionLogResponse(**l.to_dict()) for l in logs],
        total=len(logs),
    )


@app.get("/predictions/log/stats", response_model=schemas.PredictionStatsListResponse)
async def prediction_stats():
    """Get prediction volume statistics."""
    stats = repository.repo.get_stats()
    return schemas.PredictionStatsListResponse(
        stats=[schemas.PredictionStatsResponse(**s.to_dict()) for s in stats],
        total_models=len(stats),
    )


@app.get("/predictions/log/{log_id}", response_model=schemas.PredictionLogResponse)
async def get_prediction(log_id: str):
    """Get a specific logged prediction."""
    log_entry = repository.repo.get_by_id(log_id)
    if not log_entry:
        raise HTTPException(status_code=404, detail=f"Prediction log '{log_id}' not found")
    return schemas.PredictionLogResponse(**log_entry.to_dict())
