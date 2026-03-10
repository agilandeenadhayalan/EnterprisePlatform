"""
ETA Prediction Service — FastAPI application.

ETA prediction using historical, segment-based, and graph-based methods.

ROUTES:
  GET  /eta/predictions            — List all predictions
  GET  /eta/predictions/{id}       — Get prediction
  POST /eta/predict                — Predict ETA
  GET  /eta/segments               — List road segments
  GET  /eta/segments/{id}          — Get segment with speed profiles
  POST /eta/segments/{id}/speed    — Record speed observation
  GET  /eta/stats                  — ETA statistics
  GET  /health                     — Health check (provided by create_app)
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
    description="ETA prediction using historical, segment-based, and graph-based methods",
    lifespan=lifespan,
)


# ── Routes ──


@app.get("/eta/predictions", response_model=schemas.ETAPredictionListResponse)
async def list_predictions(
    method: Optional[str] = Query(default=None, description="Filter by method"),
):
    """List all ETA predictions."""
    preds = repository.repo.list_predictions(method=method)
    return schemas.ETAPredictionListResponse(
        predictions=[schemas.ETAPredictionResponse(**p.to_dict()) for p in preds],
        total=len(preds),
    )


@app.get("/eta/predictions/{pred_id}", response_model=schemas.ETAPredictionResponse)
async def get_prediction(pred_id: str):
    """Get a single ETA prediction by ID."""
    pred = repository.repo.get_prediction(pred_id)
    if not pred:
        raise HTTPException(status_code=404, detail=f"Prediction '{pred_id}' not found")
    return schemas.ETAPredictionResponse(**pred.to_dict())


@app.post("/eta/predict", response_model=schemas.ETAPredictionResponse, status_code=201)
async def predict_eta(req: schemas.ETAPredictRequest):
    """Predict ETA for a route."""
    pred = repository.repo.create_prediction(req.model_dump())
    return schemas.ETAPredictionResponse(**pred.to_dict())


@app.get("/eta/segments", response_model=schemas.RoadSegmentListResponse)
async def list_segments():
    """List all road segments."""
    segs = repository.repo.list_segments()
    return schemas.RoadSegmentListResponse(
        segments=[schemas.RoadSegmentResponse(**s.to_dict()) for s in segs],
        total=len(segs),
    )


@app.get("/eta/segments/{seg_id}", response_model=schemas.RoadSegmentDetailResponse)
async def get_segment(seg_id: str):
    """Get a road segment with its speed profiles."""
    seg = repository.repo.get_segment(seg_id)
    if not seg:
        raise HTTPException(status_code=404, detail=f"Segment '{seg_id}' not found")
    profiles = repository.repo.get_speed_profiles(seg_id)
    data = seg.to_dict()
    data["speed_profiles"] = [sp.to_dict() for sp in profiles]
    return schemas.RoadSegmentDetailResponse(**data)


@app.post("/eta/segments/{seg_id}/speed", response_model=schemas.SpeedProfileResponse, status_code=201)
async def record_speed(seg_id: str, req: schemas.SpeedObservationRequest):
    """Record a speed observation for a road segment."""
    sp = repository.repo.record_speed(seg_id, req.hour, req.speed)
    if not sp:
        raise HTTPException(status_code=404, detail=f"Segment '{seg_id}' not found")
    return schemas.SpeedProfileResponse(**sp.to_dict())


@app.get("/eta/stats", response_model=schemas.ETAStatsResponse)
async def eta_stats():
    """Get ETA prediction statistics."""
    stats = repository.repo.get_stats()
    return schemas.ETAStatsResponse(**stats)
