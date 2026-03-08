"""
Fare Calculation Service — FastAPI application.

A pure stateless calculation service with no database dependencies.

ROUTES:
  POST /fare/calculate  — Detailed fare calculation
  POST /fare/breakdown  — Fare breakdown with discount
  POST /fare/with-surge — Fare calculation with surge pricing
  GET  /health          — Health check
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mobility_common.fastapi.app import create_app

import config as fare_config
import schemas


app = create_app(
    title="Fare Calculation Service",
    version="0.1.0",
    description="Stateless fare calculation engine for Smart Mobility Platform",
)


def _calculate_fare(
    base_fare: float, distance_miles: float, per_mile_rate: float,
    duration_minutes: float, per_minute_rate: float, booking_fee: float,
    surge_multiplier: float = 1.0, discount_amount: float = 0.0,
    minimum_fare: float = 5.0,
) -> dict:
    """Core fare calculation logic."""
    distance_charge = distance_miles * per_mile_rate
    time_charge = duration_minutes * per_minute_rate
    surge_charge = (distance_charge + time_charge) * (surge_multiplier - 1.0)
    subtotal = base_fare + distance_charge + time_charge + surge_charge + booking_fee
    total = subtotal - discount_amount
    minimum_applied = total < minimum_fare
    total = max(total, minimum_fare)

    return {
        "base_fare": round(base_fare, 2),
        "distance_charge": round(distance_charge, 2),
        "time_charge": round(time_charge, 2),
        "booking_fee": round(booking_fee, 2),
        "surge_multiplier": round(surge_multiplier, 2),
        "surge_charge": round(surge_charge, 2),
        "discount_amount": round(discount_amount, 2),
        "subtotal": round(subtotal, 2),
        "total": round(total, 2),
        "minimum_fare_applied": minimum_applied,
    }


@app.post("/fare/calculate", response_model=schemas.FareBreakdownResponse)
async def calculate_fare(body: schemas.FareCalculateRequest):
    """Calculate a detailed fare breakdown."""
    result = _calculate_fare(
        base_fare=body.base_fare, distance_miles=body.distance_miles,
        per_mile_rate=body.per_mile_rate, duration_minutes=body.duration_minutes,
        per_minute_rate=body.per_minute_rate, booking_fee=body.booking_fee,
        minimum_fare=body.minimum_fare,
    )
    return schemas.FareBreakdownResponse(**result)


@app.post("/fare/breakdown", response_model=schemas.FareBreakdownResponse)
async def fare_breakdown(body: schemas.FareBreakdownRequest):
    """Calculate fare breakdown with discount applied."""
    result = _calculate_fare(
        base_fare=body.base_fare, distance_miles=body.distance_miles,
        per_mile_rate=body.per_mile_rate, duration_minutes=body.duration_minutes,
        per_minute_rate=body.per_minute_rate, booking_fee=body.booking_fee,
        discount_amount=body.discount_amount, minimum_fare=body.minimum_fare,
    )
    return schemas.FareBreakdownResponse(**result)


@app.post("/fare/with-surge", response_model=schemas.FareBreakdownResponse)
async def fare_with_surge(body: schemas.FareWithSurgeRequest):
    """Calculate fare with surge pricing and optional discount."""
    result = _calculate_fare(
        base_fare=body.base_fare, distance_miles=body.distance_miles,
        per_mile_rate=body.per_mile_rate, duration_minutes=body.duration_minutes,
        per_minute_rate=body.per_minute_rate, booking_fee=body.booking_fee,
        surge_multiplier=body.surge_multiplier, discount_amount=body.discount_amount,
        minimum_fare=body.minimum_fare,
    )
    return schemas.FareBreakdownResponse(**result)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=fare_config.settings.service_port, reload=fare_config.settings.debug)
