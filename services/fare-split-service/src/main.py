"""
Fare Split Service — FastAPI application.

ROUTES:
  POST /splits             — Create a fare split
  GET  /splits/{id}        — Get split details
  POST /splits/{id}/accept — Accept a fare split
  GET  /trips/{id}/split   — Get split for a trip
  GET  /health             — Health check
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
from mobility_common.fastapi.errors import not_found, validation_error
import config as split_config
import models  # noqa: F401
import schemas
import repository

@asynccontextmanager
async def lifespan(app):
    create_engine_and_session(split_config.settings.database_url)
    yield
    await dispose_engine()

app = create_app(title="Fare Split Service", version="0.1.0",
    description="Fare splitting between riders for Smart Mobility Platform", lifespan=lifespan)

async def _build_response(repo, split) -> schemas.SplitResponse:
    participants = await repo.get_participants(str(split.id))
    return schemas.SplitResponse(
        id=str(split.id), trip_id=str(split.trip_id), initiator_id=str(split.initiator_id),
        total_amount=split.total_amount, status=split.status, created_at=split.created_at,
        participants=[
            schemas.ParticipantResponse(id=str(p.id), split_id=str(p.split_id),
                user_id=str(p.user_id), share_amount=p.share_amount,
                status=p.status, created_at=p.created_at)
            for p in participants
        ],
    )

@app.post("/splits", response_model=schemas.SplitResponse, status_code=201)
async def create_split(body: schemas.CreateSplitRequest, db: AsyncSession = Depends(get_db)):
    repo = repository.FareSplitRepository(db)
    split = await repo.create_split(trip_id=body.trip_id, initiator_id=body.initiator_id, total_amount=body.total_amount)
    for p in body.participants:
        await repo.add_participant(split_id=str(split.id), user_id=p.user_id, share_amount=p.share_amount)
    return await _build_response(repo, split)

@app.get("/splits/{split_id}", response_model=schemas.SplitResponse)
async def get_split(split_id: str, db: AsyncSession = Depends(get_db)):
    repo = repository.FareSplitRepository(db)
    split = await repo.get_split_by_id(split_id)
    if not split:
        raise not_found("FareSplit", split_id)
    return await _build_response(repo, split)

@app.post("/splits/{split_id}/accept", response_model=schemas.AcceptSplitResponse)
async def accept_split(split_id: str, db: AsyncSession = Depends(get_db)):
    repo = repository.FareSplitRepository(db)
    split = await repo.get_split_by_id(split_id)
    if not split:
        raise not_found("FareSplit", split_id)
    return schemas.AcceptSplitResponse(
        split_id=split_id, user_id=str(split.initiator_id),
        status="accepted", message="Split accepted",
    )

@app.get("/trips/{trip_id}/split", response_model=schemas.SplitResponse)
async def get_trip_split(trip_id: str, db: AsyncSession = Depends(get_db)):
    repo = repository.FareSplitRepository(db)
    split = await repo.get_split_by_trip(trip_id)
    if not split:
        raise not_found("FareSplit for trip", trip_id)
    return await _build_response(repo, split)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=split_config.settings.service_port, reload=split_config.settings.debug)
