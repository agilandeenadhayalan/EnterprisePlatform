"""
Search service repository — stubbed search engine.

In production, this would integrate with Elasticsearch, Meilisearch,
or PostgreSQL full-text search. For now, it returns mock results.
"""

from typing import Optional, List, Dict


# Stubbed search data
MOCK_DATA = [
    {"id": "drv-1", "entity_type": "driver", "title": "John Driver", "description": "Top-rated driver"},
    {"id": "drv-2", "entity_type": "driver", "title": "Jane Driver", "description": "Premium driver"},
    {"id": "veh-1", "entity_type": "vehicle", "title": "Tesla Model 3", "description": "Electric sedan"},
    {"id": "veh-2", "entity_type": "vehicle", "title": "Toyota Camry", "description": "Standard sedan"},
    {"id": "stn-1", "entity_type": "station", "title": "Downtown Hub", "description": "Central station"},
]


class SearchRepository:
    """Stubbed search engine."""

    async def search(
        self,
        query: str,
        entity_type: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[List[Dict], int]:
        """Perform a text search. Returns (results, total_count)."""
        results = [
            item for item in MOCK_DATA
            if query.lower() in item["title"].lower() or query.lower() in (item.get("description") or "").lower()
        ]
        if entity_type:
            results = [r for r in results if r["entity_type"] == entity_type]
        total = len(results)
        return results[offset:offset + limit], total

    async def search_nearby(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 5.0,
        entity_type: Optional[str] = None,
        limit: int = 20,
    ) -> tuple[List[Dict], int]:
        """Search for entities near a location. Returns (results, total_count)."""
        # Stub: return all mock data (geospatial filtering is complex)
        results = MOCK_DATA.copy()
        if entity_type:
            results = [r for r in results if r["entity_type"] == entity_type]
        return results[:limit], len(results)

    async def get_suggestions(self, query: str, limit: int = 10) -> List[str]:
        """Get search suggestions based on partial query."""
        all_titles = [item["title"] for item in MOCK_DATA]
        return [t for t in all_titles if query.lower() in t.lower()][:limit]
