"""
Stream Processor Rides repository — in-memory storage for processed rides and stats.
"""

import time
from datetime import datetime, timezone
from typing import Optional

from models import RideEvent, RideFact, ProcessingStats


class RideProcessorRepository:
    """In-memory storage for processed ride facts and processing stats."""

    def __init__(self):
        self.processed_rides: list[RideFact] = []
        self.stats = ProcessingStats()
        self._start_time = time.time()

    def transform_ride_event(self, event: RideEvent) -> RideFact:
        """Transform a raw ride event into a fact record with derived fields."""
        pickup_dt = datetime.fromisoformat(event.pickup_at)
        dropoff_dt = datetime.fromisoformat(event.dropoff_at)

        # Calculate derived fields
        duration_seconds = (dropoff_dt - pickup_dt).total_seconds()
        trip_duration_minutes = max(duration_seconds / 60.0, 0.0)

        speed_mph = 0.0
        if trip_duration_minutes > 0 and event.distance_miles > 0:
            speed_mph = round(event.distance_miles / (trip_duration_minutes / 60.0), 2)

        total_amount = round(event.fare_amount + event.tip_amount, 2)
        pickup_hour = pickup_dt.hour
        pickup_day_of_week = pickup_dt.weekday()  # 0=Monday, 6=Sunday
        is_weekend = pickup_day_of_week >= 5  # Saturday=5, Sunday=6

        return RideFact(
            ride_id=event.ride_id,
            driver_id=event.driver_id,
            rider_id=event.rider_id,
            pickup_latitude=event.pickup_latitude,
            pickup_longitude=event.pickup_longitude,
            dropoff_latitude=event.dropoff_latitude,
            dropoff_longitude=event.dropoff_longitude,
            pickup_zone_id=event.pickup_zone_id,
            dropoff_zone_id=event.dropoff_zone_id,
            ride_status=event.ride_status,
            fare_amount=event.fare_amount,
            tip_amount=event.tip_amount,
            total_amount=total_amount,
            distance_miles=event.distance_miles,
            trip_duration_minutes=round(trip_duration_minutes, 2),
            speed_mph=speed_mph,
            pickup_at=pickup_dt,
            dropoff_at=dropoff_dt,
            pickup_hour=pickup_hour,
            pickup_day_of_week=pickup_day_of_week,
            is_weekend=is_weekend,
            vehicle_type=event.vehicle_type,
            payment_method=event.payment_method,
            surge_multiplier=event.surge_multiplier,
            processed_at=datetime.now(timezone.utc),
        )

    def process_batch(self, events: list[dict]) -> tuple[list[RideFact], int]:
        """Process a batch of raw ride event dicts. Returns (results, failed_count)."""
        results: list[RideFact] = []
        failed = 0
        start = time.time()

        for raw in events:
            try:
                event = RideEvent(**raw)
                fact = self.transform_ride_event(event)
                self.processed_rides.append(fact)
                results.append(fact)
                self.stats.events_processed += 1
            except Exception:
                failed += 1
                self.stats.events_failed += 1
                self.stats.error_count += 1

        elapsed_ms = (time.time() - start) * 1000
        if self.stats.events_processed > 0:
            total_events = self.stats.events_processed
            self.stats.avg_processing_time_ms = round(
                ((self.stats.avg_processing_time_ms * (total_events - len(results)))
                 + elapsed_ms) / total_events,
                2,
            )

        self.stats.last_processed_at = datetime.now(timezone.utc).isoformat()
        return results, failed

    def get_stats(self) -> ProcessingStats:
        """Return current processing statistics."""
        self.stats.uptime_seconds = round(time.time() - self._start_time, 2)
        return self.stats

    def get_rides_in_range(self, start_time: str, end_time: str) -> list[RideFact]:
        """Get processed rides within a time range."""
        start_dt = datetime.fromisoformat(start_time)
        end_dt = datetime.fromisoformat(end_time)
        return [
            r for r in self.processed_rides
            if start_dt <= r.pickup_at <= end_dt
        ]

    def reset_stats(self):
        """Reset processing statistics."""
        self.stats = ProcessingStats()
        self._start_time = time.time()
