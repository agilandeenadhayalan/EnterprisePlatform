"""
Vehicle Inspection Service — FastAPI application.

ROUTES:
  POST  /inspections                    — Schedule a new inspection
  GET   /vehicles/{id}/inspections      — Get inspections for a vehicle
  PATCH /inspections/{id}/status        — Update inspection status
  GET   /health                         — Health check
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mobility_common.fastapi.app import create_app
from mobility_common.fastapi.database import create_engine_and_session, get_db, dispose_engine
from mobility_common.fastapi.errors import not_found, conflict

import config as svc_config
import models  # noqa: F401
import schemas
import repository


@asynccontextmanager
async def lifespan(app):
    create_engine_and_session(svc_config.settings.database_url)
    yield
    await dispose_engine()


app = create_app(
    title="Vehicle Inspection Service",
    version="0.1.0",
    description="Vehicle inspection scheduling and tracking",
    lifespan=lifespan,
)


@app.post("/inspections", response_model=schemas.InspectionResponse, status_code=201)
async def create_inspection(
    body: schemas.CreateInspectionRequest,
    db: AsyncSession = Depends(get_db),
):
    repo = repository.VehicleInspectionRepository(db)
    insp = await repo.create_inspection(
        vehicle_id=body.vehicle_id,
        inspection_type=body.inspection_type,
        inspector_id=body.inspector_id,
        notes=body.notes,
        scheduled_at=body.scheduled_at,
    )
    return _insp_response(insp)


@app.get("/vehicles/{vehicle_id}/inspections", response_model=schemas.InspectionListResponse)
async def get_vehicle_inspections(vehicle_id: str, db: AsyncSession = Depends(get_db)):
    repo = repository.VehicleInspectionRepository(db)
    items = await repo.get_vehicle_inspections(vehicle_id)
    return schemas.InspectionListResponse(
        inspections=[_insp_response(i) for i in items],
        count=len(items),
    )


@app.patch("/inspections/{inspection_id}/status", response_model=schemas.InspectionResponse)
async def update_inspection_status(
    inspection_id: str,
    body: schemas.UpdateInspectionStatusRequest,
    db: AsyncSession = Depends(get_db),
):
    repo = repository.VehicleInspectionRepository(db)
    insp = await repo.get_inspection_by_id(inspection_id)
    if not insp:
        raise not_found("Inspection", inspection_id)

    if body.status not in repository.VALID_STATUSES:
        raise conflict(f"Invalid status '{body.status}'. Valid: {repository.VALID_STATUSES}")

    updated = await repo.update_inspection_status(
        inspection_id=inspection_id,
        status=body.status,
        notes=body.notes,
        findings=body.findings,
    )
    return _insp_response(updated)


def _insp_response(insp) -> schemas.InspectionResponse:
    return schemas.InspectionResponse(
        id=str(insp.id),
        vehicle_id=str(insp.vehicle_id),
        inspector_id=str(insp.inspector_id) if insp.inspector_id else None,
        inspection_type=insp.inspection_type,
        status=insp.status,
        notes=insp.notes,
        findings=insp.findings,
        scheduled_at=insp.scheduled_at,
        completed_at=insp.completed_at,
        created_at=insp.created_at,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=svc_config.settings.service_port, reload=svc_config.settings.debug)
