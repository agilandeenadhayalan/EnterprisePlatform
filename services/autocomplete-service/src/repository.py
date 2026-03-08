"""
Autocomplete service repository — in-memory prefix matching.

In production, this would use Redis sorted sets, a trie data structure,
or an external service like Google Places API.
"""

from typing import List, Dict


# Stubbed data for autocomplete
PLACES = [
    {"place_id": "p1", "name": "Downtown Transit Hub", "address": "100 Main St, Downtown", "latitude": 40.7128, "longitude": -74.0060},
    {"place_id": "p2", "name": "Airport Terminal A", "address": "1 Airport Blvd", "latitude": 40.6413, "longitude": -73.7781},
    {"place_id": "p3", "name": "Central Park", "address": "Central Park, New York", "latitude": 40.7829, "longitude": -73.9654},
    {"place_id": "p4", "name": "Downtown Mall", "address": "200 Commerce Ave", "latitude": 40.7580, "longitude": -73.9855},
    {"place_id": "p5", "name": "Union Station", "address": "50 Railroad Ave", "latitude": 40.7527, "longitude": -73.9772},
]

ADDRESSES = [
    {"address": "100 Main Street", "city": "New York", "state": "NY", "zip_code": "10001"},
    {"address": "200 Broadway", "city": "New York", "state": "NY", "zip_code": "10002"},
    {"address": "300 Park Avenue", "city": "New York", "state": "NY", "zip_code": "10003"},
    {"address": "400 Fifth Avenue", "city": "New York", "state": "NY", "zip_code": "10004"},
    {"address": "500 Madison Avenue", "city": "New York", "state": "NY", "zip_code": "10005"},
]


class AutocompleteRepository:
    """In-memory prefix matching for autocomplete."""

    async def autocomplete(self, query: str, limit: int = 10) -> List[Dict]:
        """General autocomplete across all categories."""
        results = []
        query_lower = query.lower()
        for p in PLACES:
            if query_lower in p["name"].lower():
                results.append({"text": p["name"], "category": "place"})
        for a in ADDRESSES:
            if query_lower in a["address"].lower():
                results.append({"text": a["address"], "category": "address"})
        return results[:limit]

    async def autocomplete_places(self, query: str, limit: int = 10) -> List[Dict]:
        """Autocomplete for places/POIs."""
        query_lower = query.lower()
        return [p for p in PLACES if query_lower in p["name"].lower()][:limit]

    async def autocomplete_addresses(self, query: str, limit: int = 10) -> List[Dict]:
        """Autocomplete for addresses."""
        query_lower = query.lower()
        return [a for a in ADDRESSES if query_lower in a["address"].lower()][:limit]
