"""
Feature Pipeline Driver — FastAPI application.

Driver feature extraction pipeline. Computes per-driver features from ride,
payment, and session data. Supports on-demand and scheduled pipeline runs.

ROUTES:
  POST /pipeline/driver/run                  — Run driver feature pipeline
  GET  /pipeline/driver/features/{driver_id} — Get computed features for a driver
  GET  /pipeline/driver/status               — Pipeline execution status
  GET  /pipeline/driver/catalog              — List all driver features
  GET  /health                               — Health check (provided by create_app)
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
    description="Driver feature extraction pipeline for the ML platform",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/pipeline/driver/run", response_model=schemas.PipelineRunResponse)
async def run_pipeline(req: schemas.PipelineRunRequest | None = None):
    """Run the driver feature computation pipeline."""
    driver_ids = req.driver_ids if req else None
    run = repository.repo.run_pipeline(driver_ids=driver_ids)
    return schemas.PipelineRunResponse(**run.to_dict())


@app.get("/pipeline/driver/features/{driver_id}", response_model=schemas.DriverFeatureSetResponse)
async def get_driver_features(driver_id: str):
    """Get computed features for a specific driver."""
    fs = repository.repo.get_features(driver_id)
    if not fs:
        raise HTTPException(status_code=404, detail=f"No features found for driver '{driver_id}'")
    return schemas.DriverFeatureSetResponse(**fs.to_dict())


@app.get("/pipeline/driver/status", response_model=schemas.PipelineStatusResponse)
async def pipeline_status():
    """Get pipeline execution history and status."""
    runs = repository.repo.get_runs()
    last_status = runs[-1].status if runs else None
    return schemas.PipelineStatusResponse(
        runs=[schemas.PipelineRunResponse(**r.to_dict()) for r in runs],
        total_runs=len(runs),
        last_run_status=last_status,
    )


@app.get("/pipeline/driver/catalog", response_model=schemas.CatalogResponse)
async def feature_catalog():
    """List all driver features in the catalog."""
    catalog = repository.repo.get_catalog()
    return schemas.CatalogResponse(
        features=[schemas.CatalogEntry(**c) for c in catalog],
        total=len(catalog),
    )
