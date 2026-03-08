"""
Route Service — FastAPI application.

ROUTES:
  POST /route/calculate — Calculate distance and ETA between two points
  GET  /route/eta       — Quick ETA lookup
  GET  /health          — Health check

No database — pure computation service using Haversine formula.
"""

import sys
from pathlib import Path

from fastapi import Query

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mobility_common.fastapi.app import create_app

import config as svc_config
import schemas
import repository


app = create_app(
    title="Route Service",
    version="0.1.0",
    description="Route calculation — distance and ETA using Haversine formula",
)


@app.post("/route/calculate", response_model=schemas.RouteCalculateResponse)
async def calculate_route(body: schemas.RouteCalculateRequest):
    """Calculate distance and estimated duration between pickup and dropoff."""
    straight_line = repository.haversine_distance(
        body.pickup_latitude, body.pickup_longitude,
        body.dropoff_latitude, body.dropoff_longitude,
    )
    road_distance = repository.estimate_road_distance(
        straight_line, svc_config.settings.road_factor,
    )
    duration = repository.estimate_duration_minutes(
        road_distance, svc_config.settings.average_speed_kmh,
    )

    return schemas.RouteCalculateResponse(
        straight_line_distance_km=round(straight_line, 2),
        estimated_road_distance_km=round(road_distance, 2),
        estimated_duration_minutes=duration,
        average_speed_kmh=svc_config.settings.average_speed_kmh,
    )


@app.get("/route/eta", response_model=schemas.EtaResponse)
async def get_eta(
    origin_lat: float = Query(..., ge=-90, le=90),
    origin_lng: float = Query(..., ge=-180, le=180),
    dest_lat: float = Query(..., ge=-90, le=90),
    dest_lng: float = Query(..., ge=-180, le=180),
):
    """Quick ETA lookup via query parameters."""
    straight_line = repository.haversine_distance(
        origin_lat, origin_lng, dest_lat, dest_lng,
    )
    road_distance = repository.estimate_road_distance(
        straight_line, svc_config.settings.road_factor,
    )
    duration = repository.estimate_duration_minutes(
        road_distance, svc_config.settings.average_speed_kmh,
    )

    return schemas.EtaResponse(
        eta_minutes=duration,
        distance_km=round(road_distance, 2),
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=svc_config.settings.service_port, reload=svc_config.settings.debug)
