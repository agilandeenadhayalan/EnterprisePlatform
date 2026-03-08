"""
Location service computation layer — mock geocoding and zone lookup.

In production, this would integrate with Google Maps, Mapbox, or similar.
For now, provides deterministic mock responses for development/testing.
"""

from typing import Optional


# Mock zone data
ZONES = [
    {
        "zone_id": "zone-manhattan",
        "name": "Manhattan",
        "city": "New York",
        "bounds": {"north": 40.882, "south": 40.700, "east": -73.907, "west": -74.020},
    },
    {
        "zone_id": "zone-brooklyn",
        "name": "Brooklyn",
        "city": "New York",
        "bounds": {"north": 40.739, "south": 40.570, "east": -73.833, "west": -74.042},
    },
    {
        "zone_id": "zone-downtown-sf",
        "name": "Downtown SF",
        "city": "San Francisco",
        "bounds": {"north": 37.800, "south": 37.770, "east": -122.390, "west": -122.420},
    },
]


def mock_geocode(address: str) -> dict:
    """Mock geocode: convert address to coordinates."""
    # Simple hash-based mock for consistent results
    addr_lower = address.lower()
    if "manhattan" in addr_lower or "new york" in addr_lower:
        return {"latitude": 40.7580, "longitude": -73.9855, "confidence": 0.95}
    elif "brooklyn" in addr_lower:
        return {"latitude": 40.6782, "longitude": -73.9442, "confidence": 0.90}
    elif "san francisco" in addr_lower or "sf" in addr_lower:
        return {"latitude": 37.7749, "longitude": -122.4194, "confidence": 0.92}
    else:
        # Generic fallback
        return {"latitude": 40.7128, "longitude": -74.0060, "confidence": 0.50}


def mock_reverse_geocode(latitude: float, longitude: float) -> dict:
    """Mock reverse geocode: convert coordinates to address."""
    if 40.70 < latitude < 40.90 and -74.05 < longitude < -73.90:
        return {
            "address": "123 Broadway, New York, NY 10006",
            "city": "New York",
            "state": "NY",
            "country": "US",
            "postal_code": "10006",
        }
    elif 37.70 < latitude < 37.85 and -122.50 < longitude < -122.35:
        return {
            "address": "456 Market St, San Francisco, CA 94105",
            "city": "San Francisco",
            "state": "CA",
            "country": "US",
            "postal_code": "94105",
        }
    else:
        return {
            "address": f"Location ({latitude:.4f}, {longitude:.4f})",
            "city": "Unknown",
            "state": None,
            "country": None,
            "postal_code": None,
        }


def get_zones() -> list[dict]:
    """Return all available service zones."""
    return ZONES
