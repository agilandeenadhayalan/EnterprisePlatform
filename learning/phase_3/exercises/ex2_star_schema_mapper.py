"""
Exercise 2: Star Schema Mapper
================================

The warehouse design module demonstrated star schemas with fact
and dimension tables. Now implement a mapper that transforms
raw ride events into star schema records.

TASK:
Given a raw ride event like:
    {"ride_id": "r1", "pickup_zone": "Manhattan", "driver_name": "Alice",
     "fare": 25.0, "distance_km": 5.2, "event_time": "2024-03-15T14:30:00"}

Produce:
1. A fact record with dimension keys and measures.
2. Dimension lookups for zone, driver, and time.
3. Handling for missing/invalid data.

WHY mappers:
- Raw data doesn't match the warehouse schema.
- Transformations standardize and enrich the data.
- Invalid data must be handled gracefully.
"""


class StarSchemaMapper:
    """
    TODO: Implement mapping from raw ride event to star schema.

    The mapper should:
    1. Extract dimension keys (zone_id, driver_id, time_id)
    2. Compute derived fields (hour, day_of_week, is_weekend)
    3. Build a fact record with foreign keys + measures
    4. Handle missing/invalid data by returning None
    """

    def __init__(self) -> None:
        """
        Initialize lookup tables for dimensions.

        Hints:
        - Create a zone name -> zone_id mapping.
        - Create a driver name -> driver_id mapping.
        - Use counters for auto-generating IDs for new entries.
        """
        # TODO: Initialize dimension lookup tables (~4 lines)
        raise NotImplementedError("Initialize lookup tables")

    def _get_or_create_zone_id(self, zone_name: str) -> str:
        """
        Look up or create a zone_id for the given zone name.

        If the zone hasn't been seen before, assign a new ID
        (e.g., "z1", "z2", ...) and remember it.
        """
        # TODO: Implement (~4 lines)
        raise NotImplementedError("Get or create zone ID")

    def _get_or_create_driver_id(self, driver_name: str) -> str:
        """Look up or create a driver_id for the given driver name."""
        # TODO: Implement (~4 lines)
        raise NotImplementedError("Get or create driver ID")

    def _extract_time_dimension(self, event_time: str) -> dict:
        """
        Extract time dimension attributes from an ISO timestamp.

        Should return a dict with:
        - time_id: derived from the date (e.g., "2024-03-15")
        - date: "2024-03-15"
        - hour: 14
        - day_of_week: "Friday"
        - is_weekend: False

        Hint: Use datetime.fromisoformat() and .strftime("%A") for day name.
        """
        # TODO: Implement (~8 lines)
        raise NotImplementedError("Extract time dimension")

    def map_ride_event(self, raw_event: dict) -> dict | None:
        """
        Map a raw ride event to a star schema fact record.

        Returns a dict with:
        - ride_id, zone_id, driver_id, time_id (dimension keys)
        - fare, distance_km (measures)
        - time attributes (hour, day_of_week, is_weekend)

        Returns None if the event is invalid (missing required fields
        or negative fare/distance).
        """
        # TODO: Implement (~15 lines)
        raise NotImplementedError("Map ride event to fact record")


# ── Verification ──


def test_basic_mapping():
    mapper = StarSchemaMapper()
    result = mapper.map_ride_event({
        "ride_id": "r1",
        "pickup_zone": "Manhattan",
        "driver_name": "Alice",
        "fare": 25.0,
        "distance_km": 5.2,
        "event_time": "2024-03-15T14:30:00",
    })
    assert result is not None
    assert result["ride_id"] == "r1"
    assert "zone_id" in result
    assert "driver_id" in result
    assert result["fare"] == 25.0


def test_invalid_event_returns_none():
    mapper = StarSchemaMapper()
    result = mapper.map_ride_event({"ride_id": "r1"})  # Missing fields
    assert result is None


def test_negative_fare_returns_none():
    mapper = StarSchemaMapper()
    result = mapper.map_ride_event({
        "ride_id": "r1",
        "pickup_zone": "Manhattan",
        "driver_name": "Alice",
        "fare": -5.0,
        "distance_km": 3.0,
        "event_time": "2024-03-15T14:30:00",
    })
    assert result is None


def test_same_zone_same_id():
    mapper = StarSchemaMapper()
    r1 = mapper.map_ride_event({
        "ride_id": "r1", "pickup_zone": "Manhattan", "driver_name": "Alice",
        "fare": 25.0, "distance_km": 5.2, "event_time": "2024-03-15T14:30:00",
    })
    r2 = mapper.map_ride_event({
        "ride_id": "r2", "pickup_zone": "Manhattan", "driver_name": "Bob",
        "fare": 30.0, "distance_km": 6.0, "event_time": "2024-03-15T15:00:00",
    })
    assert r1["zone_id"] == r2["zone_id"]  # Same zone, same ID


if __name__ == "__main__":
    try:
        test_basic_mapping()
        test_invalid_event_returns_none()
        test_negative_fare_returns_none()
        test_same_zone_same_id()
        print("All tests passed!")
    except NotImplementedError as e:
        print(f"Not yet implemented: {e}")
    except AssertionError as e:
        print(f"Test failed: {e}")
