"""
Shared utility functions used across services and learning modules.
"""

from __future__ import annotations

import math
from datetime import datetime


def haversine_distance(
    lat1: float, lon1: float,
    lat2: float, lon2: float,
) -> float:
    """
    Calculate great-circle distance between two GPS points in miles.

    Uses the Haversine formula — the standard for ride-hailing distance
    estimates before detailed routing is available.

    Args:
        lat1, lon1: First point (decimal degrees)
        lat2, lon2: Second point (decimal degrees)

    Returns:
        Distance in miles
    """
    R = 3958.8  # Earth's radius in miles

    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def format_duration(minutes: float) -> str:
    """Format duration in minutes to human-readable string."""
    if minutes < 1:
        return f"{minutes * 60:.0f}s"
    elif minutes < 60:
        return f"{minutes:.0f}min"
    else:
        hours = int(minutes // 60)
        mins = int(minutes % 60)
        return f"{hours}h {mins}min" if mins else f"{hours}h"


def format_currency(amount: float, currency: str = "USD") -> str:
    """Format monetary amount with currency symbol."""
    symbols = {"USD": "$", "EUR": "€", "GBP": "£"}
    symbol = symbols.get(currency, currency + " ")
    return f"{symbol}{amount:,.2f}"


def now_utc() -> datetime:
    """Return timezone-aware UTC now."""
    from datetime import timezone
    return datetime.now(timezone.utc)
