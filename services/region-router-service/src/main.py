"""
Region Router Service — FastAPI application.

Geo-routing, latency-based routing, and region mapping.

ROUTES:
  GET    /regions                — List all regions
  POST   /regions                — Register a region
  GET    /regions/{code}         — Get region details
  PATCH  /regions/{code}         — Update region config
  POST   /regions/route          — Route request to optimal region
  GET    /regions/routing-table  — Get current routing table
  POST   /regions/latency-check  — Check latency to all regions
  GET    /health                 — Health check (provided by create_app)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

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
    description="Geo-routing, latency-based routing, and region mapping",
    lifespan=lifespan,
)


# ── Routes ──


@app.get("/regions", response_model=list[schemas.RegionResponse])
async def list_regions():
    """List all regions."""
    regions = repository.repo.list_regions()
    return [schemas.RegionResponse(**r.to_dict()) for r in regions]


@app.post("/regions", response_model=schemas.RegionResponse, status_code=201)
async def create_region(body: schemas.RegionCreate):
    """Register a new region."""
    region = repository.repo.create_region(
        name=body.name,
        code=body.code,
        endpoint=body.endpoint,
        status=body.status,
        is_primary=body.is_primary,
        latitude=body.latitude,
        longitude=body.longitude,
        metadata=body.metadata,
    )
    return schemas.RegionResponse(**region.to_dict())


@app.get("/regions/routing-table", response_model=list[schemas.RoutingTableEntry])
async def get_routing_table():
    """Get the current routing table."""
    return repository.repo.get_routing_table()


@app.post("/regions/route", response_model=schemas.RouteResultResponse)
async def route_request(body: schemas.RouteRequest):
    """Route request to optimal region based on strategy."""
    result = repository.repo.route_request(
        latitude=body.latitude,
        longitude=body.longitude,
        strategy=body.strategy,
    )
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="No active regions available")
    return schemas.RouteResultResponse(**result.to_dict())


@app.post("/regions/latency-check", response_model=list[schemas.LatencyCheckResult])
async def latency_check():
    """Check latency to all regions."""
    return repository.repo.check_latencies()


@app.get("/regions/{code}", response_model=schemas.RegionResponse)
async def get_region(code: str):
    """Get region details by code."""
    region = repository.repo.get_region(code)
    if not region:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Region '{code}' not found")
    return schemas.RegionResponse(**region.to_dict())


@app.patch("/regions/{code}", response_model=schemas.RegionResponse)
async def update_region(code: str, body: schemas.RegionUpdate):
    """Update region configuration."""
    update_fields = body.model_dump(exclude_unset=True)
    region = repository.repo.update_region(code, **update_fields)
    if not region:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Region '{code}' not found")
    return schemas.RegionResponse(**region.to_dict())
