"""
Stream Processor Locations repository — buffered in-memory storage for location events.
"""

import time
from datetime import datetime, timezone
from typing import Optional

from models import LocationEvent, LocationFact, BufferStats

# Simple zone lookup by lat/lon ranges (simulated)
ZONE_MAP = [
    {"id": 1, "name": "Manhattan-Midtown", "lat_min": 40.748, "lat_max": 40.770, "lon_min": -73.995, "lon_max": -73.970},
    {"id": 2, "name": "Manhattan-Downtown", "lat_min": 40.700, "lat_max": 40.748, "lon_min": -74.020, "lon_max": -73.990},
    {"id": 3, "name": "Manhattan-Uptown", "lat_min": 40.770, "lat_max": 40.810, "lon_min": -73.990, "lon_max": -73.940},
    {"id": 4, "name": "Brooklyn", "lat_min": 40.620, "lat_max": 40.700, "lon_min": -74.020, "lon_max": -73.900},
    {"id": 5, "name": "Queens", "lat_min": 40.700, "lat_max": 40.780, "lon_min": -73.900, "lon_max": -73.750},
]


class LocationProcessorRepository:
    """Buffered in-memory storage for driver location facts."""

    def __init__(self, buffer_max_size: int = 100, flush_interval_seconds: int = 30):
        self.buffer: list[LocationFact] = []
        self.flushed: list[LocationFact] = []
        self.buffer_max_size = buffer_max_size
        self.flush_interval_seconds = flush_interval_seconds
        self.stats = BufferStats()
        self._start_time = time.time()
        self._last_flush_time = time.time()

    def resolve_zone(self, lat: float, lon: float) -> tuple[Optional[int], Optional[str]]:
        """Resolve a zone ID and name from lat/lon coordinates."""
        for zone in ZONE_MAP:
            if (zone["lat_min"] <= lat <= zone["lat_max"]
                    and zone["lon_min"] <= lon <= zone["lon_max"]):
                return zone["id"], zone["name"]
        return None, None

    def transform_location_event(self, event: LocationEvent) -> LocationFact:
        """Transform a raw location event into a fact record."""
        zone_id, zone_name = self.resolve_zone(event.latitude, event.longitude)
        ts = datetime.fromisoformat(event.timestamp)

        return LocationFact(
            driver_id=event.driver_id,
            latitude=event.latitude,
            longitude=event.longitude,
            heading=event.heading,
            speed_kmh=event.speed_kmh,
            accuracy_meters=event.accuracy_meters,
            zone_id=zone_id,
            zone_name=zone_name,
            status=event.status,
            ride_id=event.ride_id,
            timestamp=ts,
            processed_at=datetime.now(timezone.utc),
        )

    def process_batch(self, events: list[dict]) -> tuple[list[LocationFact], int, int]:
        """
        Process a batch of location events.
        Returns (results, flushed_count, failed_count).
        Auto-flushes when buffer exceeds max size.
        """
        results: list[LocationFact] = []
        failed = 0

        for raw in events:
            try:
                event = LocationEvent(**raw)
                fact = self.transform_location_event(event)
                self.buffer.append(fact)
                results.append(fact)
                self.stats.total_received += 1
            except Exception:
                failed += 1
                self.stats.total_errors += 1

        self.stats.last_received_at = datetime.now(timezone.utc).isoformat()

        # Auto-flush if buffer exceeds max size
        flushed = 0
        if len(self.buffer) >= self.buffer_max_size:
            flushed = self.flush()

        return results, flushed, failed

    def flush(self) -> int:
        """Flush the buffer — move all buffered records to flushed storage."""
        count = len(self.buffer)
        if count > 0:
            self.flushed.extend(self.buffer)
            self.buffer.clear()
            self.stats.total_flushed += count
            self.stats.flush_count += 1
            self.stats.last_flush_at = datetime.now(timezone.utc).isoformat()
            self._last_flush_time = time.time()
        return count

    def get_stats(self) -> BufferStats:
        """Return current buffer statistics."""
        self.stats.buffer_size = len(self.buffer)
        self.stats.uptime_seconds = round(time.time() - self._start_time, 2)
        return self.stats

    def reset(self):
        """Reset all state."""
        self.buffer.clear()
        self.flushed.clear()
        self.stats = BufferStats()
        self._start_time = time.time()
        self._last_flush_time = time.time()
