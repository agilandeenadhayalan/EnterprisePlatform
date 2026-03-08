"""Tests for ride feedback service."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest


class TestFeedbackSchemas:

    def test_create_feedback_valid(self):
        from schemas import CreateFeedbackRequest
        fb = CreateFeedbackRequest(
            trip_id="trip-1", rider_id="rider-1",
            driver_id="driver-1", rating=5,
        )
        assert fb.rating == 5

    def test_create_feedback_with_comment(self):
        from schemas import CreateFeedbackRequest
        fb = CreateFeedbackRequest(
            trip_id="trip-1", rider_id="rider-1",
            driver_id="driver-1", rating=4,
            comment="Great ride!",
        )
        assert fb.comment == "Great ride!"

    def test_create_feedback_invalid_rating_too_high(self):
        from schemas import CreateFeedbackRequest
        with pytest.raises(Exception):
            CreateFeedbackRequest(
                trip_id="trip-1", rider_id="rider-1",
                driver_id="driver-1", rating=6,
            )

    def test_create_feedback_invalid_rating_too_low(self):
        from schemas import CreateFeedbackRequest
        with pytest.raises(Exception):
            CreateFeedbackRequest(
                trip_id="trip-1", rider_id="rider-1",
                driver_id="driver-1", rating=0,
            )

    def test_feedback_response(self):
        from schemas import FeedbackResponse
        resp = FeedbackResponse(
            id="fb-1", trip_id="trip-1",
            rider_id="rider-1", driver_id="driver-1",
            rating=5, feedback_type="rider_to_driver",
        )
        assert resp.rating == 5

    def test_feedback_list_response(self):
        from schemas import FeedbackResponse, FeedbackListResponse
        items = [
            FeedbackResponse(
                id=f"fb-{i}", trip_id="trip-1",
                rider_id="rider-1", driver_id="driver-1",
                rating=i+1, feedback_type="rider_to_driver",
            )
            for i in range(3)
        ]
        resp = FeedbackListResponse(feedback=items, count=3, average_rating=2.0)
        assert resp.count == 3
        assert resp.average_rating == 2.0

    def test_feedback_list_empty(self):
        from schemas import FeedbackListResponse
        resp = FeedbackListResponse(feedback=[], count=0)
        assert resp.average_rating is None

    def test_default_feedback_type(self):
        from schemas import CreateFeedbackRequest
        fb = CreateFeedbackRequest(
            trip_id="trip-1", rider_id="rider-1",
            driver_id="driver-1", rating=3,
        )
        assert fb.feedback_type == "rider_to_driver"


class TestFeedbackConfig:

    def test_config_defaults(self):
        from config import settings
        assert settings.service_name == "ride-feedback-service"
        assert settings.service_port == 8053

    def test_database_url(self):
        from config import settings
        assert settings.database_url.startswith("postgresql+asyncpg://")
