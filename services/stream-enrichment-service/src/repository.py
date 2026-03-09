"""
Stream Enrichment Service repository — dimension cache and event enrichment.
"""

import time
from datetime import datetime, timezone
from typing import Optional

from models import RawEvent, EnrichedEvent, DimensionCache

# Pre-loaded zone dimension data (simulated from PostgreSQL/ClickHouse)
DEFAULT_ZONES = {
    1: {"name": "Newark Airport", "borough": "EWR"},
    2: {"name": "Jamaica Bay", "borough": "Queens"},
    3: {"name": "Allerton/Pelham Gardens", "borough": "Bronx"},
    4: {"name": "Alphabet City", "borough": "Manhattan"},
    7: {"name": "Astoria", "borough": "Queens"},
    12: {"name": "Battery Park City", "borough": "Manhattan"},
    13: {"name": "Bedford-Stuyvesant", "borough": "Brooklyn"},
    24: {"name": "Borough Park", "borough": "Brooklyn"},
    43: {"name": "Central Park", "borough": "Manhattan"},
    48: {"name": "Clinton East", "borough": "Manhattan"},
    50: {"name": "Clinton West", "borough": "Manhattan"},
    68: {"name": "East Chelsea", "borough": "Manhattan"},
    79: {"name": "East Village", "borough": "Manhattan"},
    87: {"name": "Financial District North", "borough": "Manhattan"},
    88: {"name": "Financial District South", "borough": "Manhattan"},
    90: {"name": "Flatiron", "borough": "Manhattan"},
    100: {"name": "Garment District", "borough": "Manhattan"},
    107: {"name": "Gramercy", "borough": "Manhattan"},
    113: {"name": "Greenwich Village North", "borough": "Manhattan"},
    114: {"name": "Greenwich Village South", "borough": "Manhattan"},
    125: {"name": "Hudson Sq", "borough": "Manhattan"},
    137: {"name": "Kips Bay", "borough": "Manhattan"},
    140: {"name": "LaGuardia Airport", "borough": "Queens"},
    141: {"name": "Lenox Hill East", "borough": "Manhattan"},
    142: {"name": "Lenox Hill West", "borough": "Manhattan"},
    143: {"name": "Lincoln Square East", "borough": "Manhattan"},
    144: {"name": "Lincoln Square West", "borough": "Manhattan"},
    148: {"name": "Lower East Side", "borough": "Manhattan"},
    151: {"name": "Manhattan Valley", "borough": "Manhattan"},
    158: {"name": "Meatpacking/West Village W", "borough": "Manhattan"},
    161: {"name": "Midtown Center", "borough": "Manhattan"},
    162: {"name": "Midtown East", "borough": "Manhattan"},
    163: {"name": "Midtown North", "borough": "Manhattan"},
    164: {"name": "Midtown South", "borough": "Manhattan"},
    170: {"name": "Murray Hill", "borough": "Manhattan"},
    186: {"name": "Penn Station/Madison Sq West", "borough": "Manhattan"},
    209: {"name": "SoHo", "borough": "Manhattan"},
    211: {"name": "SoHo", "borough": "Manhattan"},
    224: {"name": "Stuy Town/PCV", "borough": "Manhattan"},
    229: {"name": "Sutton Place/Turtle Bay North", "borough": "Manhattan"},
    230: {"name": "Times Sq/Theatre District", "borough": "Manhattan"},
    231: {"name": "TriBeCa/Civic Center", "borough": "Manhattan"},
    232: {"name": "Two Bridges/Seward Park", "borough": "Manhattan"},
    233: {"name": "UN/Turtle Bay South", "borough": "Manhattan"},
    234: {"name": "Union Sq", "borough": "Manhattan"},
    236: {"name": "Upper East Side North", "borough": "Manhattan"},
    237: {"name": "Upper East Side South", "borough": "Manhattan"},
    238: {"name": "Upper West Side North", "borough": "Manhattan"},
    239: {"name": "Upper West Side South", "borough": "Manhattan"},
    243: {"name": "Washington Heights South", "borough": "Manhattan"},
    244: {"name": "Washington Heights North", "borough": "Manhattan"},
    246: {"name": "West Chelsea/Hudson Yards", "borough": "Manhattan"},
    249: {"name": "West Village", "borough": "Manhattan"},
    261: {"name": "World Trade Center", "borough": "Manhattan"},
    262: {"name": "Yorkville East", "borough": "Manhattan"},
    263: {"name": "Yorkville West", "borough": "Manhattan"},
}

# Pre-loaded weather dimension data (simulated)
DEFAULT_WEATHER = {
    "2024-06-15-08": {"condition": "clear", "temperature_f": 72.0, "precipitation": False},
    "2024-06-15-09": {"condition": "clear", "temperature_f": 74.0, "precipitation": False},
    "2024-06-15-10": {"condition": "partly_cloudy", "temperature_f": 76.0, "precipitation": False},
    "2024-06-15-12": {"condition": "cloudy", "temperature_f": 78.0, "precipitation": False},
    "2024-06-15-14": {"condition": "rain", "temperature_f": 70.0, "precipitation": True},
    "2024-06-15-16": {"condition": "rain", "temperature_f": 68.0, "precipitation": True},
    "2024-06-15-18": {"condition": "partly_cloudy", "temperature_f": 66.0, "precipitation": False},
    "2024-06-15-20": {"condition": "clear", "temperature_f": 64.0, "precipitation": False},
    "2024-06-15-22": {"condition": "clear", "temperature_f": 62.0, "precipitation": False},
}


class EnrichmentRepository:
    """Dimension cache and event enrichment logic."""

    def __init__(self):
        self.zones: dict = {}
        self.weather: dict = {}
        self.last_refreshed_at: Optional[str] = None
        self._start_time = time.time()
        self._enrich_count = 0
        self._enrich_failed = 0

        # Load default dimensions
        self.refresh_dimensions()

    def refresh_dimensions(self) -> tuple[int, int]:
        """Refresh dimension caches from data sources (simulated)."""
        self.zones = dict(DEFAULT_ZONES)
        self.weather = dict(DEFAULT_WEATHER)
        self.last_refreshed_at = datetime.now(timezone.utc).isoformat()
        return len(self.zones), len(self.weather)

    def _get_weather_key(self, timestamp: str) -> str:
        """Extract weather lookup key (YYYY-MM-DD-HH) from ISO timestamp."""
        try:
            dt = datetime.fromisoformat(timestamp)
            return f"{dt.strftime('%Y-%m-%d')}-{dt.hour:02d}"
        except (ValueError, TypeError):
            return ""

    def enrich_event(self, raw: dict) -> Optional[EnrichedEvent]:
        """Enrich a single raw event with dimension data."""
        try:
            event = RawEvent(**raw)
        except Exception:
            self._enrich_failed += 1
            return None

        now = datetime.now(timezone.utc)

        # Zone lookups
        pickup_zone = self.zones.get(event.pickup_zone_id) if event.pickup_zone_id else None
        dropoff_zone = self.zones.get(event.dropoff_zone_id) if event.dropoff_zone_id else None

        # Weather lookup
        weather_key = self._get_weather_key(event.timestamp)
        weather = self.weather.get(weather_key)

        enriched = EnrichedEvent(
            event_id=event.event_id,
            event_type=event.event_type,
            pickup_zone_id=event.pickup_zone_id,
            pickup_zone_name=pickup_zone["name"] if pickup_zone else None,
            pickup_borough=pickup_zone["borough"] if pickup_zone else None,
            dropoff_zone_id=event.dropoff_zone_id,
            dropoff_zone_name=dropoff_zone["name"] if dropoff_zone else None,
            dropoff_borough=dropoff_zone["borough"] if dropoff_zone else None,
            weather_condition=weather["condition"] if weather else None,
            temperature_f=weather["temperature_f"] if weather else None,
            precipitation=weather["precipitation"] if weather else None,
            timestamp=event.timestamp,
            payload=event.payload,
            enriched_at=now.isoformat(),
        )

        self._enrich_count += 1
        return enriched

    def enrich_batch(self, events: list[dict]) -> tuple[list[EnrichedEvent], int]:
        """Enrich a batch of events. Returns (enriched_events, failed_count)."""
        results: list[EnrichedEvent] = []
        failed = 0

        for raw in events:
            enriched = self.enrich_event(raw)
            if enriched:
                results.append(enriched)
            else:
                failed += 1

        return results, failed

    def get_dimensions(self) -> DimensionCache:
        """Return current dimension cache info."""
        return DimensionCache(
            zones={str(k): v for k, v in self.zones.items()},
            weather=self.weather,
            last_refreshed_at=self.last_refreshed_at,
            zone_count=len(self.zones),
            weather_count=len(self.weather),
        )

    def reset(self):
        """Reset all state and reload defaults."""
        self._enrich_count = 0
        self._enrich_failed = 0
        self._start_time = time.time()
        self.refresh_dimensions()
