"""
Pricing Service — FastAPI application.

ROUTES:
  POST /estimate           — Calculate fare estimate
  POST /calculate          — Finalize fare after trip
  GET  /rules              — List all pricing rules
  GET  /rules/{vehicle_type} — Get rule for a vehicle type
  GET  /health             — Health check (provided by create_app)
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

import config as pricing_config
import models  # noqa: F401
import schemas
import repository


@asynccontextmanager
async def lifespan(app):
    """Startup: create DB engine. Shutdown: close connections."""
    create_engine_and_session(pricing_config.settings.database_url)
    yield
    await dispose_engine()


app = create_app(
    title="Pricing Service",
    version="0.1.0",
    description="Fare rules and rate calculation for Smart Mobility Platform",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/estimate", response_model=schemas.FareEstimateResponse)
async def estimate_fare(
    body: schemas.FareEstimateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Calculate a fare estimate for a trip.

    Formula: base_fare + (distance * per_mile_rate) + (duration * per_minute_rate) + booking_fee
    Apply surge multiplier to distance + time charges only.
    Enforce minimum fare.
    """
    repo = repository.PricingRepository(db)
    rule = await repo.get_rule_by_vehicle_type(body.vehicle_type)
    if not rule:
        raise not_found("PricingRule", body.vehicle_type)

    distance_charge = body.distance_miles * rule.per_mile_rate
    time_charge = body.duration_minutes * rule.per_minute_rate
    surge_charge = (distance_charge + time_charge) * (body.surge_multiplier - 1.0)
    subtotal = rule.base_fare + distance_charge + time_charge + surge_charge + rule.booking_fee
    total = max(subtotal, rule.minimum_fare)

    return schemas.FareEstimateResponse(
        vehicle_type=body.vehicle_type,
        base_fare=round(rule.base_fare, 2),
        distance_charge=round(distance_charge, 2),
        time_charge=round(time_charge, 2),
        booking_fee=round(rule.booking_fee, 2),
        surge_multiplier=body.surge_multiplier,
        surge_charge=round(surge_charge, 2),
        subtotal=round(subtotal, 2),
        total=round(total, 2),
        minimum_fare=round(rule.minimum_fare, 2),
    )


@app.post("/calculate", response_model=schemas.FareCalculateResponse)
async def calculate_fare(
    body: schemas.FareCalculateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Finalize fare after trip completion, including discounts."""
    repo = repository.PricingRepository(db)
    rule = await repo.get_rule_by_vehicle_type(body.vehicle_type)
    if not rule:
        raise not_found("PricingRule", body.vehicle_type)

    distance_charge = body.distance_miles * rule.per_mile_rate
    time_charge = body.duration_minutes * rule.per_minute_rate
    surge_charge = (distance_charge + time_charge) * (body.surge_multiplier - 1.0)
    subtotal = rule.base_fare + distance_charge + time_charge + surge_charge + rule.booking_fee
    total = max(subtotal - body.discount_amount, rule.minimum_fare)

    return schemas.FareCalculateResponse(
        vehicle_type=body.vehicle_type,
        base_fare=round(rule.base_fare, 2),
        distance_charge=round(distance_charge, 2),
        time_charge=round(time_charge, 2),
        booking_fee=round(rule.booking_fee, 2),
        surge_multiplier=body.surge_multiplier,
        surge_charge=round(surge_charge, 2),
        discount_amount=round(body.discount_amount, 2),
        subtotal=round(subtotal, 2),
        total=round(total, 2),
    )


@app.get("/rules", response_model=schemas.PricingRuleListResponse)
async def list_rules(db: AsyncSession = Depends(get_db)):
    """List all active pricing rules."""
    repo = repository.PricingRepository(db)
    rules = await repo.list_rules()
    return schemas.PricingRuleListResponse(
        rules=[
            schemas.PricingRuleResponse(
                id=str(r.id), vehicle_type=r.vehicle_type,
                base_fare=r.base_fare, per_mile_rate=r.per_mile_rate,
                per_minute_rate=r.per_minute_rate, booking_fee=r.booking_fee,
                minimum_fare=r.minimum_fare, is_active=r.is_active,
                created_at=r.created_at,
            )
            for r in rules
        ],
        count=len(rules),
    )


@app.get("/rules/{vehicle_type}", response_model=schemas.PricingRuleResponse)
async def get_rule(vehicle_type: str, db: AsyncSession = Depends(get_db)):
    """Get the pricing rule for a specific vehicle type."""
    repo = repository.PricingRepository(db)
    rule = await repo.get_rule_by_vehicle_type(vehicle_type)
    if not rule:
        raise not_found("PricingRule", vehicle_type)

    return schemas.PricingRuleResponse(
        id=str(rule.id), vehicle_type=rule.vehicle_type,
        base_fare=rule.base_fare, per_mile_rate=rule.per_mile_rate,
        per_minute_rate=rule.per_minute_rate, booking_fee=rule.booking_fee,
        minimum_fare=rule.minimum_fare, is_active=rule.is_active,
        created_at=rule.created_at,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=pricing_config.settings.service_port, reload=pricing_config.settings.debug)
