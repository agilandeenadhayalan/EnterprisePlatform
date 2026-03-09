"""
Training Data Service — FastAPI application.

Training dataset preparation and splits. Manages dataset specifications,
materialization, statistics, and sampling.

ROUTES:
  POST /training-data/datasets              — Create a dataset specification
  GET  /training-data/datasets              — List dataset specs
  GET  /training-data/datasets/{id}         — Get dataset details
  POST /training-data/datasets/{id}/prepare — Prepare/materialize the dataset
  GET  /training-data/datasets/{id}/stats   — Dataset statistics
  GET  /training-data/datasets/{id}/sample  — Get a sample from dataset
  GET  /health                              — Health check (provided by create_app)
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
    description="Training dataset preparation, splits, and sampling",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/training-data/datasets", response_model=schemas.DatasetSpecResponse, status_code=201)
async def create_dataset(body: schemas.DatasetCreateRequest):
    """Create a new dataset specification."""
    ds = repository.repo.create_dataset(
        name=body.name,
        feature_names=body.feature_names,
        label_column=body.label_column,
        date_range=body.date_range,
        split_ratio=body.split_ratio,
        sampling_strategy=body.sampling_strategy,
    )
    return schemas.DatasetSpecResponse(**ds.to_dict())


@app.get("/training-data/datasets", response_model=schemas.DatasetSpecListResponse)
async def list_datasets():
    """List all dataset specifications."""
    datasets = repository.repo.list_datasets()
    return schemas.DatasetSpecListResponse(
        datasets=[schemas.DatasetSpecResponse(**d.to_dict()) for d in datasets],
        total=len(datasets),
    )


@app.get("/training-data/datasets/{dataset_id}", response_model=schemas.DatasetSpecResponse)
async def get_dataset(dataset_id: str):
    """Get details for a specific dataset specification."""
    ds = repository.repo.get_dataset(dataset_id)
    if ds is None:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")
    return schemas.DatasetSpecResponse(**ds.to_dict())


@app.post("/training-data/datasets/{dataset_id}/prepare", response_model=schemas.DatasetSpecResponse)
async def prepare_dataset(dataset_id: str):
    """Prepare and materialize a dataset for training."""
    ds = repository.repo.prepare_dataset(dataset_id)
    if ds is None:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")
    return schemas.DatasetSpecResponse(**ds.to_dict())


@app.get("/training-data/datasets/{dataset_id}/stats", response_model=schemas.DatasetStatsResponse)
async def get_dataset_stats(dataset_id: str):
    """Get statistical summary of a dataset."""
    ds = repository.repo.get_dataset(dataset_id)
    if ds is None:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")
    stats = repository.repo.get_stats(dataset_id)
    if stats is None:
        raise HTTPException(status_code=400, detail=f"Dataset {dataset_id} has not been prepared yet")
    return schemas.DatasetStatsResponse(**stats.to_dict())


@app.get("/training-data/datasets/{dataset_id}/sample", response_model=schemas.DatasetSampleResponse)
async def get_dataset_sample(dataset_id: str):
    """Get a sample of rows from the dataset."""
    ds = repository.repo.get_dataset(dataset_id)
    if ds is None:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")
    sample = repository.repo.get_sample(dataset_id)
    if sample is None:
        raise HTTPException(status_code=400, detail=f"Dataset {dataset_id} has no sample data available")
    columns = ds.feature_names + [ds.label_column]
    return schemas.DatasetSampleResponse(
        dataset_id=dataset_id,
        columns=columns,
        rows=sample,
        total_sampled=len(sample),
    )
