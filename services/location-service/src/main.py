"""
Location Service — FastAPI application.

ROUTES:
  POST /geocode          — Convert address to coordinates
  POST /reverse-geocode  — Convert coordinates to address
  GET  /zones            — List available service zones
  GET  /health           — Health check

No database — mock geocoding service for development.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mobility_common.fastapi.app import create_app

import config as svc_config
import schemas
import repository


app = create_app(
    title="Location Service",
    version="0.1.0",
    description="Geocoding, reverse geocoding, and zone lookup",
)


@app.post("/geocode", response_model=schemas.GeocodeResponse)
async def geocode(body: schemas.GeocodeRequest):
    result = repository.mock_geocode(body.address)
    return schemas.GeocodeResponse(address=body.address, **result)


@app.post("/reverse-geocode", response_model=schemas.ReverseGeocodeResponse)
async def reverse_geocode(body: schemas.ReverseGeocodeRequest):
    result = repository.mock_reverse_geocode(body.latitude, body.longitude)
    return schemas.ReverseGeocodeResponse(
        latitude=body.latitude,
        longitude=body.longitude,
        **result,
    )


@app.get("/zones", response_model=schemas.ZoneListResponse)
async def list_zones():
    zones = repository.get_zones()
    return schemas.ZoneListResponse(
        zones=[schemas.ZoneResponse(**z) for z in zones],
        count=len(zones),
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=svc_config.settings.service_port, reload=svc_config.settings.debug)
