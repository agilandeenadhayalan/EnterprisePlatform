"""
Toll Service — FastAPI application.

Stateless toll estimation and calculation service with mock data.

ROUTES:
  GET  /tolls/estimate  — Estimate tolls for origin/destination
  POST /tolls/calculate — Calculate tolls for a specific route
  GET  /health          — Health check
"""
import sys
import math
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import Query
from mobility_common.fastapi.app import create_app
import config as toll_config
import schemas


app = create_app(title="Toll Service", version="0.1.0",
    description="Toll estimation and calculation for Smart Mobility Platform")


def _haversine(lat1, lon1, lat2, lon2) -> float:
    """Distance in miles between two coordinates."""
    R = 3959
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def _estimate_toll(distance_miles: float, vehicle_type: str) -> float:
    """Stub toll estimation based on distance and vehicle type."""
    # Mock: $0.15/mile for cars, $0.25/mile for trucks
    rates = {"car": 0.15, "suv": 0.18, "truck": 0.25}
    rate = rates.get(vehicle_type, 0.15)
    # Only charge tolls for trips over 5 miles (highway likely)
    if distance_miles < 5.0:
        return 0.0
    return round(distance_miles * rate, 2)


@app.get("/tolls/estimate", response_model=schemas.TollEstimateResponse)
async def estimate_tolls(
    origin_lat: float = Query(..., ge=-90, le=90),
    origin_lon: float = Query(..., ge=-180, le=180),
    destination_lat: float = Query(..., ge=-90, le=90),
    destination_lon: float = Query(..., ge=-180, le=180),
    vehicle_type: str = Query(default="car"),
):
    """Estimate tolls between origin and destination."""
    distance = _haversine(origin_lat, origin_lon, destination_lat, destination_lon)
    toll = _estimate_toll(distance, vehicle_type)

    segments = []
    if toll > 0:
        segments.append(schemas.TollSegment(
            name="Highway Toll", cost=toll,
            lat=(origin_lat + destination_lat) / 2,
            lon=(origin_lon + destination_lon) / 2,
        ))

    return schemas.TollEstimateResponse(
        estimated_toll=toll, toll_segments=segments,
        confidence=0.7 if toll > 0 else 0.9,
    )


@app.post("/tolls/calculate", response_model=schemas.TollCalculateResponse)
async def calculate_tolls(body: schemas.TollCalculateRequest):
    """Calculate tolls for a specific route."""
    total_distance = 0.0
    for i in range(len(body.route_points) - 1):
        p1, p2 = body.route_points[i], body.route_points[i + 1]
        total_distance += _haversine(p1["lat"], p1["lon"], p2["lat"], p2["lon"])

    toll = _estimate_toll(total_distance, body.vehicle_type)
    segments = []
    if toll > 0:
        mid = len(body.route_points) // 2
        mp = body.route_points[mid]
        segments.append(schemas.TollSegment(name="Highway Toll", cost=toll, lat=mp["lat"], lon=mp["lon"]))

    return schemas.TollCalculateResponse(
        total_toll=toll, toll_segments=segments,
        route_has_tolls=toll > 0,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=toll_config.settings.service_port, reload=toll_config.settings.debug)
