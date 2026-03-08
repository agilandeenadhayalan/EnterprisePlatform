"""
Tests for search service — schema validation, config, and repository logic.
No database needed — these are pure unit tests.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest
from pydantic import ValidationError


class TestSearchSchemas:
    """Verify Pydantic schema validation for search requests/responses."""

    def test_search_request_valid(self):
        from schemas import SearchRequest
        req = SearchRequest(query="driver")
        assert req.limit == 20
        assert req.offset == 0

    def test_search_request_with_filter(self):
        from schemas import SearchRequest
        req = SearchRequest(query="John", entity_type="driver", limit=10)
        assert req.entity_type == "driver"

    def test_search_request_rejects_empty_query(self):
        from schemas import SearchRequest
        with pytest.raises(ValidationError):
            SearchRequest(query="")

    def test_nearby_search_request_valid(self):
        from schemas import NearbySearchRequest
        req = NearbySearchRequest(latitude=40.7128, longitude=-74.0060)
        assert req.radius_km == 5.0

    def test_search_result_item(self):
        from schemas import SearchResultItem
        item = SearchResultItem(
            id="drv-1", entity_type="driver", title="John Driver"
        )
        assert item.score == 0.0
        assert item.metadata == {}

    def test_search_response(self):
        from schemas import SearchResponse, SearchResultItem
        resp = SearchResponse(
            results=[
                SearchResultItem(id="1", entity_type="driver", title="John")
            ],
            total=1,
            query="John",
        )
        assert resp.total == 1

    def test_suggestion_response(self):
        from schemas import SuggestionResponse
        resp = SuggestionResponse(suggestions=["driver", "downtown"], query="d")
        assert len(resp.suggestions) == 2


class TestSearchRepository:
    """Verify stubbed search repository logic."""

    @pytest.mark.asyncio
    async def test_search_returns_results(self):
        from repository import SearchRepository
        repo = SearchRepository()
        results, total = await repo.search("driver")
        assert total > 0

    @pytest.mark.asyncio
    async def test_search_filters_by_entity_type(self):
        from repository import SearchRepository
        repo = SearchRepository()
        results, total = await repo.search("driver", entity_type="vehicle")
        assert all(r["entity_type"] == "vehicle" for r in results)

    @pytest.mark.asyncio
    async def test_get_suggestions(self):
        from repository import SearchRepository
        repo = SearchRepository()
        suggestions = await repo.get_suggestions("driv")
        assert len(suggestions) > 0


class TestSearchConfig:
    """Verify search service configuration defaults."""

    def test_config_defaults(self):
        from config import settings
        assert settings.service_name == "search-service"
        assert settings.service_port == 8097

    def test_kafka_config(self):
        from config import settings
        assert settings.kafka_bootstrap_servers == "kafka:9092"
