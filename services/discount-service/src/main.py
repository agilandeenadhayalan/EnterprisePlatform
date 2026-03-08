"""
Discount Service — FastAPI application.

ROUTES:
  POST /discounts/validate — Check if a discount code is valid
  POST /discounts/apply    — Apply discount to a fare
  GET  /discounts/active   — List active discounts
  POST /discounts          — Create a new discount code
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

import config as discount_config
import models  # noqa: F401
import schemas
import repository


@asynccontextmanager
async def lifespan(app):
    create_engine_and_session(discount_config.settings.database_url)
    yield
    await dispose_engine()


app = create_app(
    title="Discount Service",
    version="0.1.0",
    description="Promo code validation and application for Smart Mobility Platform",
    lifespan=lifespan,
)


@app.post("/discounts/validate", response_model=schemas.ValidateDiscountResponse)
async def validate_discount(body: schemas.ValidateDiscountRequest, db: AsyncSession = Depends(get_db)):
    """Check if a discount code is valid."""
    repo = repository.DiscountRepository(db)
    discount = await repo.get_by_code(body.code)

    if not discount:
        return schemas.ValidateDiscountResponse(code=body.code, is_valid=False, reason="Code not found")
    if not discount.is_active:
        return schemas.ValidateDiscountResponse(code=body.code, is_valid=False, reason="Code is inactive")
    if discount.max_uses and discount.current_uses >= discount.max_uses:
        return schemas.ValidateDiscountResponse(code=body.code, is_valid=False, reason="Code usage limit reached")
    if body.fare_amount and discount.min_fare_amount and body.fare_amount < discount.min_fare_amount:
        return schemas.ValidateDiscountResponse(code=body.code, is_valid=False, reason="Fare below minimum")

    return schemas.ValidateDiscountResponse(
        code=body.code, is_valid=True,
        discount_type=discount.discount_type,
        discount_value=discount.discount_value,
    )


@app.post("/discounts/apply", response_model=schemas.ApplyDiscountResponse)
async def apply_discount(body: schemas.ApplyDiscountRequest, db: AsyncSession = Depends(get_db)):
    """Apply a discount code to a fare amount."""
    repo = repository.DiscountRepository(db)
    discount = await repo.get_by_code(body.code)
    if not discount or not discount.is_active:
        raise not_found("Discount", body.code)

    if discount.discount_type == "percentage":
        discount_amount = body.fare_amount * (discount.discount_value / 100.0)
    else:
        discount_amount = discount.discount_value

    if discount.max_discount_amount:
        discount_amount = min(discount_amount, discount.max_discount_amount)

    final_fare = max(body.fare_amount - discount_amount, 0)
    await repo.increment_uses(body.code)

    return schemas.ApplyDiscountResponse(
        code=body.code, original_fare=round(body.fare_amount, 2),
        discount_amount=round(discount_amount, 2), final_fare=round(final_fare, 2),
    )


@app.get("/discounts/active", response_model=schemas.DiscountListResponse)
async def list_active_discounts(db: AsyncSession = Depends(get_db)):
    repo = repository.DiscountRepository(db)
    discounts = await repo.list_active()
    return schemas.DiscountListResponse(
        discounts=[
            schemas.DiscountResponse(
                id=str(d.id), code=d.code, description=d.description,
                discount_type=d.discount_type, discount_value=d.discount_value,
                max_uses=d.max_uses, current_uses=d.current_uses,
                min_fare_amount=d.min_fare_amount, max_discount_amount=d.max_discount_amount,
                is_active=d.is_active, valid_from=d.valid_from, valid_until=d.valid_until,
                created_at=d.created_at,
            )
            for d in discounts
        ],
        count=len(discounts),
    )


@app.post("/discounts", response_model=schemas.DiscountResponse, status_code=201)
async def create_discount(body: schemas.CreateDiscountRequest, db: AsyncSession = Depends(get_db)):
    repo = repository.DiscountRepository(db)
    discount = await repo.create_discount(
        code=body.code, description=body.description,
        discount_type=body.discount_type, discount_value=body.discount_value,
        max_uses=body.max_uses, min_fare_amount=body.min_fare_amount,
        max_discount_amount=body.max_discount_amount,
        valid_from=body.valid_from, valid_until=body.valid_until,
    )
    return schemas.DiscountResponse(
        id=str(discount.id), code=discount.code, description=discount.description,
        discount_type=discount.discount_type, discount_value=discount.discount_value,
        max_uses=discount.max_uses, current_uses=discount.current_uses,
        min_fare_amount=discount.min_fare_amount, max_discount_amount=discount.max_discount_amount,
        is_active=discount.is_active, valid_from=discount.valid_from, valid_until=discount.valid_until,
        created_at=discount.created_at,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=discount_config.settings.service_port, reload=discount_config.settings.debug)
