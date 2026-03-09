"""
Data Catalog Service — FastAPI application.

Dataset metadata registry — tracks what data exists, where it lives, and its schema.

ROUTES:
  GET    /catalog/datasets          — List all datasets (supports ?store= filter, ?q= search)
  POST   /catalog/datasets          — Register a new dataset
  GET    /catalog/datasets/{id}     — Get dataset details
  PATCH  /catalog/datasets/{id}     — Update dataset metadata
  DELETE /catalog/datasets/{id}     — Remove dataset from catalog
  GET    /catalog/search            — Search datasets by keyword
  GET    /catalog/stats             — Catalog statistics (count per store, total size)
  GET    /health                    — Health check (provided by create_app)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

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
    description="Dataset metadata registry for Smart Mobility Platform",
    lifespan=lifespan,
)


# ── Routes ──


@app.get("/catalog/datasets", response_model=schemas.DatasetListResponse)
async def list_datasets(
    store: str = Query(default=None, description="Filter by store (clickhouse, minio, postgres)"),
    q: str = Query(default=None, description="Search keyword"),
):
    """List all datasets, optionally filtered by store or search keyword."""
    datasets = repository.repo.list_datasets(store=store, q=q)
    return schemas.DatasetListResponse(
        datasets=[schemas.DatasetResponse(**d.to_dict()) for d in datasets],
        total=len(datasets),
    )


@app.post("/catalog/datasets", response_model=schemas.DatasetResponse, status_code=201)
async def create_dataset(body: schemas.DatasetCreate):
    """Register a new dataset in the catalog."""
    dataset = repository.repo.create_dataset(
        name=body.name,
        description=body.description,
        store=body.store,
        location=body.location,
        schema_fields=body.schema_fields,
        format=body.format,
        owner=body.owner,
        tags=body.tags,
        size_bytes=body.size_bytes,
        record_count=body.record_count,
    )
    return schemas.DatasetResponse(**dataset.to_dict())


@app.get("/catalog/datasets/{dataset_id}", response_model=schemas.DatasetResponse)
async def get_dataset(dataset_id: str):
    """Get dataset details by ID."""
    dataset = repository.repo.get_dataset(dataset_id)
    if not dataset:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found")
    return schemas.DatasetResponse(**dataset.to_dict())


@app.patch("/catalog/datasets/{dataset_id}", response_model=schemas.DatasetResponse)
async def update_dataset(dataset_id: str, body: schemas.DatasetUpdate):
    """Update dataset metadata."""
    update_fields = body.model_dump(exclude_unset=True)
    dataset = repository.repo.update_dataset(dataset_id, **update_fields)
    if not dataset:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found")
    return schemas.DatasetResponse(**dataset.to_dict())


@app.delete("/catalog/datasets/{dataset_id}", status_code=204)
async def delete_dataset(dataset_id: str):
    """Remove a dataset from the catalog."""
    deleted = repository.repo.delete_dataset(dataset_id)
    if not deleted:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found")


@app.get("/catalog/search", response_model=schemas.DatasetListResponse)
async def search_datasets(
    q: str = Query(..., description="Search keyword"),
):
    """Search datasets by keyword across name, description, and tags."""
    datasets = repository.repo.search_datasets(q)
    return schemas.DatasetListResponse(
        datasets=[schemas.DatasetResponse(**d.to_dict()) for d in datasets],
        total=len(datasets),
    )


@app.get("/catalog/stats", response_model=schemas.CatalogStatsResponse)
async def catalog_stats():
    """Get catalog statistics — count per store, total size, total records."""
    stats = repository.repo.get_stats()
    return schemas.CatalogStatsResponse(**stats)
