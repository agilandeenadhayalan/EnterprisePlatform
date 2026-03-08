"""
Search Service — FastAPI application.

ROUTES:
  POST /search             — Perform a text search
  GET  /search/suggestions — Get search suggestions
  POST /search/nearby      — Search for entities near a location
  GET  /health             — Health check (provided by create_app)
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
    title="Search Service",
    version="0.1.0",
    description="Unified search for Smart Mobility Platform",
)

search_repo = repository.SearchRepository()


# ── Routes ──


@app.post("/search", response_model=schemas.SearchResponse)
async def search(body: schemas.SearchRequest):
    """Perform a text search across platform entities."""
    results, total = await search_repo.search(
        query=body.query,
        entity_type=body.entity_type,
        limit=body.limit,
        offset=body.offset,
    )
    return schemas.SearchResponse(
        results=[
            schemas.SearchResultItem(**r, score=1.0)
            for r in results
        ],
        total=total,
        query=body.query,
    )


@app.get("/search/suggestions", response_model=schemas.SuggestionResponse)
async def suggestions(q: str = ""):
    """Get search suggestions based on a partial query."""
    suggestions = await search_repo.get_suggestions(q)
    return schemas.SuggestionResponse(suggestions=suggestions, query=q)


@app.post("/search/nearby", response_model=schemas.SearchResponse)
async def search_nearby(body: schemas.NearbySearchRequest):
    """Search for entities near a geographic location."""
    results, total = await search_repo.search_nearby(
        latitude=body.latitude,
        longitude=body.longitude,
        radius_km=body.radius_km,
        entity_type=body.entity_type,
        limit=body.limit,
    )
    return schemas.SearchResponse(
        results=[
            schemas.SearchResultItem(**r, score=1.0)
            for r in results
        ],
        total=total,
        query=f"nearby({body.latitude},{body.longitude})",
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=service_config.settings.service_port,
        reload=service_config.settings.debug,
    )
