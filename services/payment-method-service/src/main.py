"""
Payment Method Service — FastAPI application.

ROUTES:
  POST   /payment-methods              — Add a payment method
  GET    /users/{id}/payment-methods    — List user's payment methods
  DELETE /payment-methods/{id}          — Remove a payment method
  PATCH  /payment-methods/{id}/default  — Set as default
  GET    /health                        — Health check
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
import config as pm_config
import models  # noqa: F401
import schemas
import repository

@asynccontextmanager
async def lifespan(app):
    create_engine_and_session(pm_config.settings.database_url)
    yield
    await dispose_engine()

app = create_app(title="Payment Method Service", version="0.1.0",
    description="Payment method management for Smart Mobility Platform", lifespan=lifespan)

def _to_response(pm) -> schemas.PaymentMethodResponse:
    return schemas.PaymentMethodResponse(
        id=str(pm.id), user_id=str(pm.user_id), method_type=pm.method_type,
        provider=pm.provider, last_four=pm.last_four,
        expiry_month=pm.expiry_month, expiry_year=pm.expiry_year,
        is_default=pm.is_default, is_active=pm.is_active, created_at=pm.created_at,
    )

@app.post("/payment-methods", response_model=schemas.PaymentMethodResponse, status_code=201)
async def create_payment_method(body: schemas.CreatePaymentMethodRequest, db: AsyncSession = Depends(get_db)):
    repo = repository.PaymentMethodRepository(db)
    pm = await repo.create(
        user_id=body.user_id, method_type=body.method_type, provider=body.provider,
        last_four=body.last_four, expiry_month=body.expiry_month, expiry_year=body.expiry_year,
        is_default=body.is_default, token_ref=body.token_ref,
    )
    return _to_response(pm)

@app.get("/users/{user_id}/payment-methods", response_model=schemas.PaymentMethodListResponse)
async def list_user_payment_methods(user_id: str, db: AsyncSession = Depends(get_db)):
    repo = repository.PaymentMethodRepository(db)
    methods = await repo.list_by_user(user_id)
    return schemas.PaymentMethodListResponse(payment_methods=[_to_response(m) for m in methods], count=len(methods))

@app.delete("/payment-methods/{pm_id}", status_code=204)
async def delete_payment_method(pm_id: str, db: AsyncSession = Depends(get_db)):
    repo = repository.PaymentMethodRepository(db)
    deleted = await repo.delete_method(pm_id)
    if not deleted:
        raise not_found("PaymentMethod", pm_id)

@app.patch("/payment-methods/{pm_id}/default", response_model=schemas.PaymentMethodResponse)
async def set_default_payment_method(pm_id: str, db: AsyncSession = Depends(get_db)):
    repo = repository.PaymentMethodRepository(db)
    pm = await repo.get_by_id(pm_id)
    if not pm:
        raise not_found("PaymentMethod", pm_id)
    updated = await repo.set_default(str(pm.user_id), pm_id)
    return _to_response(updated)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=pm_config.settings.service_port, reload=pm_config.settings.debug)
