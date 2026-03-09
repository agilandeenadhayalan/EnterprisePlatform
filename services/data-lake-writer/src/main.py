"""
Data Lake Writer Service — FastAPI application.

Manages the Medallion architecture: writes data to Bronze/Silver/Gold layers
in the data lake and handles transformations between layers.

ROUTES:
  POST /write/{layer}              — Write data to a specific layer (bronze/silver/gold)
  GET  /layers                     — List all layers with stats (object count, total size)
  GET  /layers/{layer}/stats       — Detailed stats for a single layer
  POST /transform/bronze-to-silver — Transform Bronze raw data to Silver cleaned Parquet
  POST /transform/silver-to-gold   — Aggregate Silver to Gold analytics-ready data
  GET  /health                     — Health check (provided by create_app)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Query

# Add project root for mobility-common imports
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
# Add service src for local imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mobility_common.fastapi.app import create_app

import config as service_config
import schemas
import repository


@asynccontextmanager
async def lifespan(app):
    """Startup/shutdown lifecycle."""
    yield


app = create_app(
    title=service_config.settings.service_name,
    version="0.1.0",
    description="Medallion architecture data lake writer — Bronze/Silver/Gold layers",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/write/{layer}", response_model=schemas.WriteResponse, status_code=201)
async def write_to_layer(layer: str, body: schemas.WriteRequest):
    """
    Write data to a specific Medallion layer.

    - Bronze: raw, unprocessed data as-is from source systems
    - Silver: cleaned and validated data (nulls removed, types consistent)
    - Gold: aggregated, analytics-ready data
    """
    valid_layers = ["bronze", "silver", "gold"]
    if layer not in valid_layers:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Invalid layer '{layer}'. Must be one of: {', '.join(valid_layers)}",
        )

    record = repository.repo.write_record(
        layer=layer,
        source=body.source,
        data=body.data,
        metadata=body.metadata,
    )

    return schemas.WriteResponse(
        record_id=record.record_id,
        layer=record.layer,
        source=record.source,
        timestamp=record.timestamp,
    )


@app.get("/layers", response_model=schemas.AllLayersStatsResponse)
async def list_layers():
    """List all Medallion layers with stats (object count, total size)."""
    stats = repository.repo.get_all_layer_stats()
    layer_responses = [
        schemas.LayerStatsResponse(
            layer=s.layer,
            object_count=s.object_count,
            total_size_bytes=s.total_size_bytes,
        )
        for s in stats
    ]
    return schemas.AllLayersStatsResponse(
        layers=layer_responses,
        total_objects=sum(s.object_count for s in stats),
        total_size_bytes=sum(s.total_size_bytes for s in stats),
    )


@app.get("/layers/{layer}/stats", response_model=schemas.LayerStatsResponse)
async def layer_stats(layer: str):
    """Get detailed stats for a specific Medallion layer."""
    valid_layers = ["bronze", "silver", "gold"]
    if layer not in valid_layers:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Invalid layer '{layer}'. Must be one of: {', '.join(valid_layers)}",
        )

    stats = repository.repo.get_layer_stats(layer)
    return schemas.LayerStatsResponse(
        layer=stats.layer,
        object_count=stats.object_count,
        total_size_bytes=stats.total_size_bytes,
    )


@app.post("/transform/bronze-to-silver", response_model=schemas.TransformJobResponse)
async def transform_bronze_to_silver(body: schemas.TransformRequest = None):
    """
    Transform Bronze raw data to Silver cleaned format.

    Cleaning operations:
    - Remove null values
    - Ensure consistent types
    - Deduplicate by source + data content hash
    """
    if body is None:
        body = schemas.TransformRequest()

    job = repository.repo.transform_bronze_to_silver(
        source_filter=body.source_filter,
        limit=body.limit,
    )
    return schemas.TransformJobResponse(**job.to_dict())


@app.post("/transform/silver-to-gold", response_model=schemas.TransformJobResponse)
async def transform_silver_to_gold(body: schemas.TransformRequest = None):
    """
    Aggregate Silver data to Gold analytics-ready format.

    Aggregation operations:
    - Group records by source
    - Count records per source
    - Compute numeric summary statistics (sum, avg, min, max)
    """
    if body is None:
        body = schemas.TransformRequest()

    job = repository.repo.transform_silver_to_gold(
        source_filter=body.source_filter,
        limit=body.limit,
    )
    return schemas.TransformJobResponse(**job.to_dict())
