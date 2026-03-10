"""
Cost Tracking Service — FastAPI application.

Cost per trip/request and resource allocation tracking.

ROUTES:
  GET    /costs/allocations       — List cost allocations
  POST   /costs/allocations       — Create allocation rule
  GET    /costs/allocations/{id}  — Get allocation details
  POST   /costs/record            — Record a cost event
  GET    /costs/records           — List cost records
  GET    /costs/summary           — Cost summary by service/resource
  GET    /costs/per-trip          — Unit economics (cost per trip)
  GET    /health                  — Health check (provided by create_app)
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
    description="Cost per trip/request and resource allocation tracking",
    lifespan=lifespan,
)


# ── Routes ──


@app.get("/costs/allocations", response_model=list[schemas.AllocationResponse])
async def list_allocations():
    """List all cost allocations."""
    allocs = repository.repo.list_allocations()
    return [schemas.AllocationResponse(**a.to_dict()) for a in allocs]


@app.post("/costs/allocations", response_model=schemas.AllocationResponse, status_code=201)
async def create_allocation(body: schemas.AllocationCreate):
    """Create an allocation rule."""
    alloc = repository.repo.create_allocation(
        service_name=body.service_name,
        resource_type=body.resource_type,
        cost_per_unit=body.cost_per_unit,
        unit=body.unit,
        tags=body.tags,
        period=body.period,
    )
    return schemas.AllocationResponse(**alloc.to_dict())


@app.get("/costs/allocations/{alloc_id}", response_model=schemas.AllocationResponse)
async def get_allocation(alloc_id: str):
    """Get allocation details."""
    alloc = repository.repo.get_allocation(alloc_id)
    if not alloc:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Allocation '{alloc_id}' not found")
    return schemas.AllocationResponse(**alloc.to_dict())


@app.post("/costs/record", response_model=schemas.CostRecordResponse, status_code=201)
async def record_cost(body: schemas.CostRecordCreate):
    """Record a cost event."""
    record = repository.repo.record_cost(
        allocation_id=body.allocation_id,
        quantity=body.quantity,
        trip_id=body.trip_id,
        request_id=body.request_id,
    )
    if not record:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Allocation '{body.allocation_id}' not found")
    return schemas.CostRecordResponse(**record.to_dict())


@app.get("/costs/records", response_model=list[schemas.CostRecordResponse])
async def list_records(service: str | None = None):
    """List cost records with optional service filter."""
    records = repository.repo.list_records(service=service)
    return [schemas.CostRecordResponse(**r.to_dict()) for r in records]


@app.get("/costs/summary", response_model=list[schemas.CostSummaryResponse])
async def cost_summary():
    """Cost summary by service/resource."""
    return repository.repo.get_summary()


@app.get("/costs/per-trip", response_model=schemas.PerTripCostResponse)
async def per_trip_cost():
    """Unit economics — cost per trip."""
    return repository.repo.get_per_trip_cost()
