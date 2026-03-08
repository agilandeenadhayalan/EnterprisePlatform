"""
Dynamic Pricing AI Service — FastAPI application.

Stub ML prediction service with mock responses.

ROUTES:
  POST /predict-price     — Predict optimal price for a trip
  GET  /demand-heatmap    — Get demand heatmap data
  GET  /supply-heatmap    — Get supply heatmap data
  GET  /health            — Health check
"""

import sys
import math
import random
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mobility_common.fastapi.app import create_app

import config as ai_config
import schemas


app = create_app(
    title="Dynamic Pricing AI Service",
    version="0.1.0",
    description="ML-based price prediction stubs for Smart Mobility Platform",
)


def _haversine_distance(lat1, lon1, lat2, lon2) -> float:
    """Calculate approximate distance in miles between two coordinates."""
    R = 3959  # Earth's radius in miles
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


@app.post("/predict-price", response_model=schemas.PredictPriceResponse)
async def predict_price(body: schemas.PredictPriceRequest):
    """Predict fare using stub ML model."""
    distance = _haversine_distance(body.pickup_lat, body.pickup_lon, body.dropoff_lat, body.dropoff_lon)

    # Stub prediction: base fare + distance-based + time-of-day factor
    base = 2.50
    per_mile = 1.75
    time_factor = 1.0 + (0.3 if 7 <= body.hour_of_day <= 9 or 16 <= body.hour_of_day <= 19 else 0.0)
    holiday_factor = 1.2 if body.is_holiday else 1.0

    predicted = (base + distance * per_mile) * time_factor * holiday_factor
    surge = round(time_factor * holiday_factor, 2)

    return schemas.PredictPriceResponse(
        predicted_fare=round(predicted, 2),
        confidence=round(random.uniform(0.75, 0.95), 2),
        surge_recommendation=surge,
        model_version="stub-v1.0",
    )


@app.get("/demand-heatmap", response_model=schemas.HeatmapResponse)
async def demand_heatmap():
    """Get mock demand heatmap data."""
    cells = [
        schemas.HeatmapCell(
            lat=30.27 + i * 0.01, lon=-97.74 + j * 0.01,
            intensity=round(random.uniform(0.1, 1.0), 2),
        )
        for i in range(5) for j in range(5)
    ]
    return schemas.HeatmapResponse(
        heatmap=cells,
        generated_at=datetime.now(timezone.utc).isoformat(),
        grid_size=25,
    )


@app.get("/supply-heatmap", response_model=schemas.HeatmapResponse)
async def supply_heatmap():
    """Get mock supply heatmap data."""
    cells = [
        schemas.HeatmapCell(
            lat=30.27 + i * 0.01, lon=-97.74 + j * 0.01,
            intensity=round(random.uniform(0.2, 0.9), 2),
        )
        for i in range(5) for j in range(5)
    ]
    return schemas.HeatmapResponse(
        heatmap=cells,
        generated_at=datetime.now(timezone.utc).isoformat(),
        grid_size=25,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=ai_config.settings.service_port, reload=ai_config.settings.debug)
