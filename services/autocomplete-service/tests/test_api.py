"""
Tests for autocomplete service — schema validation, config, and repository logic.
No database needed — these are pure unit tests.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest


class TestAutocompleteSchemas:
    """Verify Pydantic schema validation for autocomplete responses."""

    def test_autocomplete_item(self):
        from schemas import AutocompleteItem
        item = AutocompleteItem(text="Downtown Hub", category="place")
        assert item.metadata is None

    def test_autocomplete_response(self):
        from schemas import AutocompleteItem, AutocompleteResponse
        resp = AutocompleteResponse(
            query="down",
            suggestions=[AutocompleteItem(text="Downtown", category="place")],
            count=1,
        )
        assert resp.count == 1

    def test_place_autocomplete_item(self):
        from schemas import PlaceAutocompleteItem
        item = PlaceAutocompleteItem(
            place_id="p1",
            name="Downtown Hub",
            address="100 Main St",
            latitude=40.7128,
            longitude=-74.0060,
        )
        assert item.latitude == 40.7128

    def test_place_autocomplete_response(self):
        from schemas import PlaceAutocompleteItem, PlaceAutocompleteResponse
        resp = PlaceAutocompleteResponse(
            query="down",
            places=[PlaceAutocompleteItem(place_id="p1", name="Downtown", address="100 Main St")],
            count=1,
        )
        assert resp.count == 1

    def test_address_autocomplete_item(self):
        from schemas import AddressAutocompleteItem
        item = AddressAutocompleteItem(
            address="100 Main Street",
            city="New York",
            state="NY",
        )
        assert item.zip_code is None

    def test_address_autocomplete_response(self):
        from schemas import AddressAutocompleteItem, AddressAutocompleteResponse
        resp = AddressAutocompleteResponse(
            query="100",
            addresses=[AddressAutocompleteItem(address="100 Main St", city="NY", state="NY")],
            count=1,
        )
        assert resp.count == 1


class TestAutocompleteRepository:
    """Verify in-memory autocomplete repository logic."""

    @pytest.mark.asyncio
    async def test_autocomplete_returns_results(self):
        from repository import AutocompleteRepository
        repo = AutocompleteRepository()
        results = await repo.autocomplete("down")
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_autocomplete_places(self):
        from repository import AutocompleteRepository
        repo = AutocompleteRepository()
        results = await repo.autocomplete_places("airport")
        assert len(results) > 0
        assert results[0]["name"] == "Airport Terminal A"


class TestAutocompleteConfig:
    """Verify autocomplete service configuration defaults."""

    def test_config_defaults(self):
        from config import settings
        assert settings.service_name == "autocomplete-service"
        assert settings.service_port == 8098

    def test_kafka_config(self):
        from config import settings
        assert settings.kafka_bootstrap_servers == "kafka:9092"
