"""Tests for location service."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest


class TestGeocoding:

    def test_geocode_nyc(self):
        from repository import mock_geocode
        result = mock_geocode("Times Square, New York")
        assert result["latitude"] == 40.7580
        assert result["confidence"] > 0.9

    def test_geocode_sf(self):
        from repository import mock_geocode
        result = mock_geocode("Market Street, San Francisco")
        assert 37.0 < result["latitude"] < 38.0

    def test_geocode_unknown(self):
        from repository import mock_geocode
        result = mock_geocode("Random Unknown Place")
        assert result["confidence"] <= 0.5

    def test_reverse_geocode_nyc(self):
        from repository import mock_reverse_geocode
        result = mock_reverse_geocode(40.7580, -73.9855)
        assert "New York" in result["address"]
        assert result["city"] == "New York"

    def test_reverse_geocode_sf(self):
        from repository import mock_reverse_geocode
        result = mock_reverse_geocode(37.7749, -122.4194)
        assert "San Francisco" in result["address"]

    def test_reverse_geocode_unknown(self):
        from repository import mock_reverse_geocode
        result = mock_reverse_geocode(0.0, 0.0)
        assert result["city"] == "Unknown"


class TestZones:

    def test_get_zones(self):
        from repository import get_zones
        zones = get_zones()
        assert len(zones) == 3

    def test_zone_structure(self):
        from repository import get_zones
        zone = get_zones()[0]
        assert "zone_id" in zone
        assert "bounds" in zone
        assert "north" in zone["bounds"]


class TestLocationConfig:

    def test_config_defaults(self):
        from config import settings
        assert settings.service_name == "location-service"
        assert settings.service_port == 8056
