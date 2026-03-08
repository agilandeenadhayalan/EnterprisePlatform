"""
Autocomplete Service — FastAPI application.

ROUTES:
  GET /autocomplete           — General autocomplete suggestions
  GET /autocomplete/places    — Place/POI autocomplete
  GET /autocomplete/addresses — Address autocomplete
  GET /health                 — Health check (provided by create_app)
"""

import sys
from pathlib import Path

# Add project root for mobility-common imports
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
# Add service src for local imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mobility_common.fastapi.app import create_app

import config as service_config
import schemas
import repository


app = create_app(
    title="Autocomplete Service",
    version="0.1.0",
    description="Autocomplete and type-ahead suggestions for Smart Mobility Platform",
)

ac_repo = repository.AutocompleteRepository()


# ── Routes ──


@app.get("/autocomplete", response_model=schemas.AutocompleteResponse)
async def autocomplete(q: str = ""):
    """Get general autocomplete suggestions."""
    results = await ac_repo.autocomplete(q, limit=service_config.settings.max_suggestions)
    return schemas.AutocompleteResponse(
        query=q,
        suggestions=[schemas.AutocompleteItem(**r) for r in results],
        count=len(results),
    )


@app.get("/autocomplete/places", response_model=schemas.PlaceAutocompleteResponse)
async def autocomplete_places(q: str = ""):
    """Get place/POI autocomplete suggestions."""
    results = await ac_repo.autocomplete_places(q, limit=service_config.settings.max_suggestions)
    return schemas.PlaceAutocompleteResponse(
        query=q,
        places=[schemas.PlaceAutocompleteItem(**r) for r in results],
        count=len(results),
    )


@app.get("/autocomplete/addresses", response_model=schemas.AddressAutocompleteResponse)
async def autocomplete_addresses(q: str = ""):
    """Get address autocomplete suggestions."""
    results = await ac_repo.autocomplete_addresses(q, limit=service_config.settings.max_suggestions)
    return schemas.AddressAutocompleteResponse(
        query=q,
        addresses=[schemas.AddressAutocompleteItem(**r) for r in results],
        count=len(results),
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=service_config.settings.service_port,
        reload=service_config.settings.debug,
    )
