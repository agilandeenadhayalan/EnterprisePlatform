"""
Payout Service — FastAPI application.

ROUTES:
  POST /payouts              — Create a payout
  GET  /drivers/{id}/payouts — List driver's payouts
  GET  /payouts/{id}         — Get payout details
  GET  /payouts/pending      — List pending payouts
  GET  /health               — Health check
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
from mobility_common.fastapi.errors import not_found
import config as payout_config
import models  # noqa: F401
import schemas
import repository

@asynccontextmanager
async def lifespan(app):
    create_engine_and_session(payout_config.settings.database_url)
    yield
    await dispose_engine()

app = create_app(title="Payout Service", version="0.1.0",
    description="Driver payout processing for Smart Mobility Platform", lifespan=lifespan)

def _to_response(p) -> schemas.PayoutResponse:
    return schemas.PayoutResponse(
        id=str(p.id), driver_id=str(p.driver_id), amount=p.amount,
        currency=p.currency, status=p.status, payout_method=p.payout_method,
        reference=p.reference, period_start=p.period_start,
        period_end=p.period_end, created_at=p.created_at,
    )

@app.post("/payouts", response_model=schemas.PayoutResponse, status_code=201)
async def create_payout(body: schemas.CreatePayoutRequest, db: AsyncSession = Depends(get_db)):
    repo = repository.PayoutRepository(db)
    payout = await repo.create_payout(
        driver_id=body.driver_id, amount=body.amount, currency=body.currency,
        payout_method=body.payout_method, period_start=body.period_start, period_end=body.period_end,
    )
    return _to_response(payout)

@app.get("/payouts/pending", response_model=schemas.PayoutListResponse)
async def list_pending_payouts(db: AsyncSession = Depends(get_db)):
    repo = repository.PayoutRepository(db)
    payouts = await repo.list_pending()
    return schemas.PayoutListResponse(payouts=[_to_response(p) for p in payouts], count=len(payouts))

@app.get("/drivers/{driver_id}/payouts", response_model=schemas.PayoutListResponse)
async def list_driver_payouts(driver_id: str, db: AsyncSession = Depends(get_db)):
    repo = repository.PayoutRepository(db)
    payouts = await repo.list_by_driver(driver_id)
    return schemas.PayoutListResponse(payouts=[_to_response(p) for p in payouts], count=len(payouts))

@app.get("/payouts/{payout_id}", response_model=schemas.PayoutResponse)
async def get_payout(payout_id: str, db: AsyncSession = Depends(get_db)):
    repo = repository.PayoutRepository(db)
    payout = await repo.get_by_id(payout_id)
    if not payout:
        raise not_found("Payout", payout_id)
    return _to_response(payout)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=payout_config.settings.service_port, reload=payout_config.settings.debug)
