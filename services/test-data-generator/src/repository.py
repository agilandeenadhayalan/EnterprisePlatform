"""
Test data generator repository — in-memory event generation and state management.

Generates realistic fake ride data with NYC zone IDs (1-265), fare ranges,
and GPS coordinates. In production, events would be pushed to Kafka.
"""

import uuid
import random
from datetime import datetime, timedelta
from typing import Any, Optional

from models import GeneratorConfig, GeneratorStatus, EventTemplate, GeneratedEvent


# NYC bounding box for GPS coordinate generation
NYC_LAT_MIN, NYC_LAT_MAX = 40.4774, 40.9176
NYC_LNG_MIN, NYC_LNG_MAX = -74.2591, -73.7004

# Sample driver names
DRIVER_NAMES = [
    "John Smith", "Maria Garcia", "David Kim", "Sarah Johnson",
    "Ahmed Hassan", "Lisa Chen", "James Brown", "Ana Rodriguez",
    "Wei Zhang", "Fatima Ali", "Carlos Lopez", "Priya Patel",
    "Michael O'Brien", "Yuki Tanaka", "Omar Ibrahim",
]

PAYMENT_METHODS = ["credit_card", "debit_card", "cash", "wallet", "apple_pay", "google_pay"]
RIDE_STATUSES = ["requested", "accepted", "in_progress", "completed", "cancelled"]
VEHICLE_TYPES = ["economy", "comfort", "premium", "xl", "pool"]

# Event templates
TEMPLATES = [
    EventTemplate(
        template_id="ride_event",
        name="Ride Event",
        description="A complete ride lifecycle event with pickup/dropoff locations, fare, and status",
        event_type="ride",
        fields=[
            {"name": "ride_id", "type": "uuid"},
            {"name": "driver_id", "type": "string"},
            {"name": "rider_id", "type": "string"},
            {"name": "pickup_zone_id", "type": "int (1-265)"},
            {"name": "dropoff_zone_id", "type": "int (1-265)"},
            {"name": "pickup_lat", "type": "float"},
            {"name": "pickup_lng", "type": "float"},
            {"name": "dropoff_lat", "type": "float"},
            {"name": "dropoff_lng", "type": "float"},
            {"name": "fare_amount", "type": "float"},
            {"name": "tip_amount", "type": "float"},
            {"name": "distance_miles", "type": "float"},
            {"name": "duration_minutes", "type": "float"},
            {"name": "status", "type": "string"},
            {"name": "vehicle_type", "type": "string"},
        ],
        sample={
            "ride_id": "550e8400-e29b-41d4-a716-446655440000",
            "driver_id": "drv-0001",
            "rider_id": "rdr-1234",
            "pickup_zone_id": 161,
            "dropoff_zone_id": 236,
            "pickup_lat": 40.7549,
            "pickup_lng": -73.9840,
            "dropoff_lat": 40.7736,
            "dropoff_lng": -73.9566,
            "fare_amount": 18.50,
            "tip_amount": 3.70,
            "distance_miles": 2.3,
            "duration_minutes": 12.5,
            "status": "completed",
            "vehicle_type": "comfort",
        },
    ),
    EventTemplate(
        template_id="location_event",
        name="Location Update",
        description="Real-time GPS location update from a driver's device",
        event_type="location",
        fields=[
            {"name": "driver_id", "type": "string"},
            {"name": "lat", "type": "float"},
            {"name": "lng", "type": "float"},
            {"name": "heading", "type": "float (0-360)"},
            {"name": "speed_mph", "type": "float"},
            {"name": "accuracy_meters", "type": "float"},
            {"name": "zone_id", "type": "int (1-265)"},
        ],
        sample={
            "driver_id": "drv-0042",
            "lat": 40.7580,
            "lng": -73.9855,
            "heading": 45.0,
            "speed_mph": 18.5,
            "accuracy_meters": 5.2,
            "zone_id": 231,
        },
    ),
    EventTemplate(
        template_id="payment_event",
        name="Payment Event",
        description="Payment transaction for a completed ride",
        event_type="payment",
        fields=[
            {"name": "payment_id", "type": "uuid"},
            {"name": "ride_id", "type": "uuid"},
            {"name": "amount", "type": "float"},
            {"name": "tip", "type": "float"},
            {"name": "total", "type": "float"},
            {"name": "method", "type": "string"},
            {"name": "status", "type": "string"},
            {"name": "currency", "type": "string"},
        ],
        sample={
            "payment_id": "pay-abcd-1234",
            "ride_id": "550e8400-e29b-41d4-a716-446655440000",
            "amount": 18.50,
            "tip": 3.70,
            "total": 22.20,
            "method": "credit_card",
            "status": "completed",
            "currency": "USD",
        },
    ),
    EventTemplate(
        template_id="driver_event",
        name="Driver Status Event",
        description="Driver availability and status changes",
        event_type="driver",
        fields=[
            {"name": "driver_id", "type": "string"},
            {"name": "driver_name", "type": "string"},
            {"name": "status", "type": "string"},
            {"name": "zone_id", "type": "int (1-265)"},
            {"name": "vehicle_type", "type": "string"},
            {"name": "rating", "type": "float"},
        ],
        sample={
            "driver_id": "drv-0042",
            "driver_name": "John Smith",
            "status": "online",
            "zone_id": 161,
            "vehicle_type": "comfort",
            "rating": 4.85,
        },
    ),
]

VALID_EVENT_TYPES = {t.event_type for t in TEMPLATES}
VALID_MODES = {"replay", "synthetic", "stress"}


class GeneratorRepository:
    """In-memory event generator and state tracker."""

    def __init__(self):
        self._is_running: bool = False
        self._mode: Optional[str] = None
        self._events_generated: int = 0
        self._events_per_second: int = 0
        self._started_at: Optional[str] = None
        self._elapsed_seconds: float = 0.0
        self._generated_events: list[GeneratedEvent] = []
        self._rng = random.Random(42)

    def get_status(self) -> GeneratorStatus:
        """Get current generator status."""
        return GeneratorStatus(
            is_running=self._is_running,
            mode=self._mode,
            events_generated=self._events_generated,
            events_per_second=self._events_per_second,
            elapsed_seconds=self._elapsed_seconds,
            started_at=self._started_at,
        )

    def start(self, mode: str, events_per_second: int, duration_seconds: int) -> GeneratorStatus:
        """Start event generation (mock: simulates immediate generation)."""
        self._is_running = True
        self._mode = mode
        self._events_per_second = events_per_second
        self._started_at = datetime.utcnow().isoformat()

        # Simulate generating some events
        simulated_count = min(events_per_second * duration_seconds, 1000)
        for _ in range(simulated_count):
            event = self._generate_single_event("ride")
            self._generated_events.append(event)

        self._events_generated += simulated_count
        self._elapsed_seconds = float(duration_seconds)
        self._is_running = False  # Completed

        return self.get_status()

    def stop(self) -> GeneratorStatus:
        """Stop event generation."""
        self._is_running = False
        return self.get_status()

    def generate_batch(self, count: int, event_type: str) -> list[GeneratedEvent]:
        """Generate a batch of events of the specified type."""
        events = []
        for _ in range(count):
            event = self._generate_single_event(event_type)
            events.append(event)
            self._generated_events.append(event)

        self._events_generated += count
        return events

    def get_templates(self) -> list[EventTemplate]:
        """Get available event templates."""
        return TEMPLATES

    def _generate_single_event(self, event_type: str) -> GeneratedEvent:
        """Generate a single realistic event."""
        event_id = str(uuid.uuid4())
        timestamp = (
            datetime.utcnow() - timedelta(seconds=self._rng.randint(0, 86400))
        ).isoformat() + "Z"

        if event_type == "ride":
            data = self._generate_ride_data()
        elif event_type == "location":
            data = self._generate_location_data()
        elif event_type == "payment":
            data = self._generate_payment_data()
        elif event_type == "driver":
            data = self._generate_driver_data()
        else:
            data = self._generate_ride_data()

        return GeneratedEvent(
            event_id=event_id,
            event_type=event_type,
            timestamp=timestamp,
            data=data,
        )

    def _generate_ride_data(self) -> dict[str, Any]:
        """Generate realistic ride event data."""
        fare = round(self._rng.uniform(5.0, 75.0), 2)
        tip = round(fare * self._rng.uniform(0.0, 0.3), 2)
        distance = round(self._rng.uniform(0.3, 20.0), 1)
        duration = round(distance * self._rng.uniform(3.0, 8.0), 1)

        return {
            "ride_id": str(uuid.uuid4()),
            "driver_id": f"drv-{self._rng.randint(1, 500):04d}",
            "rider_id": f"rdr-{self._rng.randint(1, 10000):05d}",
            "pickup_zone_id": self._rng.randint(1, 265),
            "dropoff_zone_id": self._rng.randint(1, 265),
            "pickup_lat": round(self._rng.uniform(NYC_LAT_MIN, NYC_LAT_MAX), 6),
            "pickup_lng": round(self._rng.uniform(NYC_LNG_MIN, NYC_LNG_MAX), 6),
            "dropoff_lat": round(self._rng.uniform(NYC_LAT_MIN, NYC_LAT_MAX), 6),
            "dropoff_lng": round(self._rng.uniform(NYC_LNG_MIN, NYC_LNG_MAX), 6),
            "fare_amount": fare,
            "tip_amount": tip,
            "distance_miles": distance,
            "duration_minutes": duration,
            "status": self._rng.choice(RIDE_STATUSES),
            "vehicle_type": self._rng.choice(VEHICLE_TYPES),
        }

    def _generate_location_data(self) -> dict[str, Any]:
        """Generate realistic GPS location update."""
        return {
            "driver_id": f"drv-{self._rng.randint(1, 500):04d}",
            "lat": round(self._rng.uniform(NYC_LAT_MIN, NYC_LAT_MAX), 6),
            "lng": round(self._rng.uniform(NYC_LNG_MIN, NYC_LNG_MAX), 6),
            "heading": round(self._rng.uniform(0, 360), 1),
            "speed_mph": round(self._rng.uniform(0, 45), 1),
            "accuracy_meters": round(self._rng.uniform(1.0, 15.0), 1),
            "zone_id": self._rng.randint(1, 265),
        }

    def _generate_payment_data(self) -> dict[str, Any]:
        """Generate realistic payment event data."""
        amount = round(self._rng.uniform(5.0, 75.0), 2)
        tip = round(amount * self._rng.uniform(0.0, 0.25), 2)
        return {
            "payment_id": str(uuid.uuid4()),
            "ride_id": str(uuid.uuid4()),
            "amount": amount,
            "tip": tip,
            "total": round(amount + tip, 2),
            "method": self._rng.choice(PAYMENT_METHODS),
            "status": "completed",
            "currency": "USD",
        }

    def _generate_driver_data(self) -> dict[str, Any]:
        """Generate realistic driver status event."""
        return {
            "driver_id": f"drv-{self._rng.randint(1, 500):04d}",
            "driver_name": self._rng.choice(DRIVER_NAMES),
            "status": self._rng.choice(["online", "offline", "busy", "idle"]),
            "zone_id": self._rng.randint(1, 265),
            "vehicle_type": self._rng.choice(VEHICLE_TYPES),
            "rating": round(self._rng.uniform(3.5, 5.0), 2),
        }


# Singleton repository instance
repo = GeneratorRepository()
