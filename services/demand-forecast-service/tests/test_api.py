"""
Tests for the Demand Forecast service API.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_list_forecasts(client: AsyncClient):
    resp = await client.get("/demand/forecasts")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 8
    assert len(data["forecasts"]) == 8


@pytest.mark.anyio
async def test_filter_zone(client: AsyncClient):
    resp = await client.get("/demand/forecasts", params={"zone_id": "zone-001"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    for f in data["forecasts"]:
        assert f["zone_id"] == "zone-001"


@pytest.mark.anyio
async def test_filter_method(client: AsyncClient):
    resp = await client.get("/demand/forecasts", params={"method": "time_series"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    for f in data["forecasts"]:
        assert f["method"] == "time_series"


@pytest.mark.anyio
async def test_get_forecast(client: AsyncClient):
    resp = await client.get("/demand/forecasts/fc-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["zone_id"] == "zone-001"
    assert data["method"] == "time_series"


@pytest.mark.anyio
async def test_not_found(client: AsyncClient):
    resp = await client.get("/demand/forecasts/fc-999")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_create_forecast(client: AsyncClient):
    payload = {
        "zone_id": "zone-001",
        "time_slot": "2026-03-11T08:00",
        "method": "regression",
    }
    resp = await client.post("/demand/forecast", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["zone_id"] == "zone-001"
    assert data["method"] == "regression"
    assert data["predicted_demand"] > 0


@pytest.mark.anyio
async def test_forecast_includes_uncertainty(client: AsyncClient):
    payload = {
        "zone_id": "zone-002",
        "time_slot": "2026-03-11T12:00",
        "method": "time_series",
    }
    resp = await client.post("/demand/forecast", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert "uncertainty_low" in data
    assert "uncertainty_high" in data
    assert data["uncertainty_low"] < data["predicted_demand"]
    assert data["uncertainty_high"] > data["predicted_demand"]


@pytest.mark.anyio
async def test_list_zones(client: AsyncClient):
    resp = await client.get("/demand/zones")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 10
    assert len(data["zones"]) == 10


@pytest.mark.anyio
async def test_get_zone(client: AsyncClient):
    resp = await client.get("/demand/zones/zone-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["zone_name"] == "manhattan_midtown"


@pytest.mark.anyio
async def test_zone_not_found(client: AsyncClient):
    resp = await client.get("/demand/zones/zone-999")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_weather_impact_create(client: AsyncClient):
    payload = {"condition": "fog", "impact_coefficient": 0.6}
    resp = await client.post("/demand/weather-impact", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["condition"] == "fog"
    assert data["impact_coefficient"] == 0.6


@pytest.mark.anyio
async def test_weather_impact_update(client: AsyncClient):
    payload = {"condition": "rain", "impact_coefficient": 0.65}
    resp = await client.post("/demand/weather-impact", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["condition"] == "rain"
    assert data["impact_coefficient"] == 0.65


@pytest.mark.anyio
async def test_stats(client: AsyncClient):
    resp = await client.get("/demand/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_forecasts"] == 8
    assert data["avg_uncertainty_range"] > 0


@pytest.mark.anyio
async def test_stats_by_method(client: AsyncClient):
    resp = await client.get("/demand/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["by_method"]["time_series"] == 3
    assert data["by_method"]["regression"] == 2


@pytest.mark.anyio
async def test_forecast_weather_factor(client: AsyncClient):
    resp = await client.get("/demand/forecasts/fc-001")
    assert resp.status_code == 200
    data = resp.json()
    assert 0.0 <= data["weather_factor"] <= 1.0


@pytest.mark.anyio
async def test_uncertainty_bounds_valid(client: AsyncClient):
    resp = await client.get("/demand/forecasts")
    assert resp.status_code == 200
    for f in resp.json()["forecasts"]:
        assert f["uncertainty_low"] <= f["uncertainty_high"]
