"""
Refund Service — FastAPI application.

ROUTES:
  POST  /refunds               — Create a refund request
  GET   /refunds/{id}          — Get refund details
  GET   /payments/{id}/refunds — List refunds for a payment
  PATCH /refunds/{id}/approve  — Approve a refund
  GET   /health                — Health check
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
import config as refund_config
import models  # noqa: F401
import schemas
import repository

@asynccontextmanager
async def lifespan(app):
    create_engine_and_session(refund_config.settings.database_url)
    yield
    await dispose_engine()

app = create_app(title="Refund Service", version="0.1.0",
    description="Refund processing for Smart Mobility Platform", lifespan=lifespan)

def _to_response(r) -> schemas.RefundResponse:
    return schemas.RefundResponse(
        id=str(r.id), payment_id=str(r.payment_id), rider_id=str(r.rider_id),
        amount=r.amount, reason=r.reason, status=r.status,
        approved_by=str(r.approved_by) if r.approved_by else None,
        created_at=r.created_at, updated_at=r.updated_at,
    )

@app.post("/refunds", response_model=schemas.RefundResponse, status_code=201)
async def create_refund(body: schemas.CreateRefundRequest, db: AsyncSession = Depends(get_db)):
    repo = repository.RefundRepository(db)
    refund = await repo.create_refund(payment_id=body.payment_id, rider_id=body.rider_id, amount=body.amount, reason=body.reason)
    return _to_response(refund)

@app.get("/refunds/{refund_id}", response_model=schemas.RefundResponse)
async def get_refund(refund_id: str, db: AsyncSession = Depends(get_db)):
    repo = repository.RefundRepository(db)
    refund = await repo.get_by_id(refund_id)
    if not refund:
        raise not_found("Refund", refund_id)
    return _to_response(refund)

@app.get("/payments/{payment_id}/refunds", response_model=schemas.RefundListResponse)
async def list_payment_refunds(payment_id: str, db: AsyncSession = Depends(get_db)):
    repo = repository.RefundRepository(db)
    refunds = await repo.list_by_payment(payment_id)
    return schemas.RefundListResponse(refunds=[_to_response(r) for r in refunds], count=len(refunds))

@app.patch("/refunds/{refund_id}/approve", response_model=schemas.RefundResponse)
async def approve_refund(refund_id: str, body: schemas.ApproveRefundRequest, db: AsyncSession = Depends(get_db)):
    repo = repository.RefundRepository(db)
    refund = await repo.get_by_id(refund_id)
    if not refund:
        raise not_found("Refund", refund_id)
    updated = await repo.approve(refund_id, body.approved_by)
    return _to_response(updated)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=refund_config.settings.service_port, reload=refund_config.settings.debug)
