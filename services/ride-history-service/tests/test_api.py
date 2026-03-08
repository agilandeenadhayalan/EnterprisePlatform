"""Tests for ride history service."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest


class TestHistorySchemas:

    def test_history_trip_response(self):
        from schemas import HistoryTripResponse
        resp = HistoryTripResponse(
            id="trip-1", rider_id="rider-1",
            status="completed", fare_amount=25.50,
        )
        assert resp.fare_amount == 25.50

    def test_history_trip_optional_fields(self):
        from schemas import HistoryTripResponse
        resp = HistoryTripResponse(
            id="trip-1", rider_id="rider-1", status="completed",
        )
        assert resp.driver_id is None
        assert resp.actual_distance_km is None

    def test_history_list_response(self):
        from schemas import HistoryTripResponse, HistoryListResponse
        trips = [
            HistoryTripResponse(
                id=f"trip-{i}", rider_id="rider-1",
                status="completed", fare_amount=float(i * 10),
            )
            for i in range(5)
        ]
        resp = HistoryListResponse(trips=trips, count=5)
        assert resp.count == 5

    def test_history_list_empty(self):
        from schemas import HistoryListResponse
        resp = HistoryListResponse(trips=[], count=0)
        assert resp.count == 0

    def test_rider_stats_response(self):
        from schemas import RiderStatsResponse
        stats = RiderStatsResponse(
            rider_id="rider-1",
            total_trips=20,
            completed_trips=18,
            cancelled_trips=2,
            total_spent=450.0,
            average_fare=25.0,
        )
        assert stats.total_trips == 20
        assert stats.completed_trips == 18

    def test_rider_stats_no_average(self):
        from schemas import RiderStatsResponse
        stats = RiderStatsResponse(
            rider_id="rider-1",
            total_trips=0,
            completed_trips=0,
            cancelled_trips=0,
            total_spent=0.0,
        )
        assert stats.average_fare is None

    def test_default_currency(self):
        from schemas import HistoryTripResponse
        resp = HistoryTripResponse(
            id="trip-1", rider_id="rider-1", status="completed",
        )
        assert resp.currency == "USD"


class TestHistoryConfig:

    def test_config_defaults(self):
        from config import settings
        assert settings.service_name == "ride-history-service"
        assert settings.service_port == 8054

    def test_database_url(self):
        from config import settings
        assert settings.database_url.startswith("postgresql+asyncpg://")

    def test_kafka_config(self):
        from config import settings
        assert settings.kafka_bootstrap_servers == "kafka:9092"
