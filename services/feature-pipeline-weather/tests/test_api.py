"""
Tests for the Feature Pipeline Weather service API.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_get_weather_features_for_station(client: AsyncClient):
    resp = await client.get("/pipeline/weather/features", params={"station_id": "station_01"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] > 0
    assert data["feature_sets"][0]["station_id"] == "station_01"


@pytest.mark.anyio
async def test_get_weather_features_specific_hour(client: AsyncClient):
    resp = await client.get("/pipeline/weather/features", params={
        "station_id": "station_01",
        "hour": "2026-03-05T12:00:00Z",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    fs = data["feature_sets"][0]
    assert fs["hour"] == "2026-03-05T12:00:00Z"
    assert "weather_temperature" in fs["features"]


@pytest.mark.anyio
async def test_get_weather_features_not_found(client: AsyncClient):
    resp = await client.get("/pipeline/weather/features", params={"station_id": "station_99"})
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_weather_features_have_all_fields(client: AsyncClient):
    resp = await client.get("/pipeline/weather/features", params={
        "station_id": "station_02",
        "hour": "2026-03-06T08:00:00Z",
    })
    assert resp.status_code == 200
    features = resp.json()["feature_sets"][0]["features"]
    assert "weather_temperature" in features
    assert "weather_precipitation" in features
    assert "weather_wind_speed" in features
    assert "weather_visibility" in features
    assert "weather_humidity" in features
    assert "weather_pressure" in features
    assert "weather_bucket" in features
    assert "weather_is_severe" in features


@pytest.mark.anyio
async def test_weather_bucket_values(client: AsyncClient):
    resp = await client.get("/pipeline/weather/features", params={"station_id": "station_01"})
    data = resp.json()
    valid_buckets = {"clear", "rain", "snow", "fog", "storm"}
    for fs in data["feature_sets"]:
        assert fs["features"]["weather_bucket"] in valid_buckets


@pytest.mark.anyio
async def test_run_pipeline(client: AsyncClient):
    resp = await client.post("/pipeline/weather/run", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["features_computed"] > 0


@pytest.mark.anyio
async def test_run_pipeline_specific_stations(client: AsyncClient):
    resp = await client.post("/pipeline/weather/run", json={"station_ids": ["station_01", "station_02"]})
    assert resp.status_code == 200
    assert resp.json()["features_computed"] == 16  # 2 stations * 8 features


@pytest.mark.anyio
async def test_run_pipeline_no_body(client: AsyncClient):
    resp = await client.post("/pipeline/weather/run")
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"


@pytest.mark.anyio
async def test_catalog(client: AsyncClient):
    resp = await client.get("/pipeline/weather/catalog")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 8
    names = [f["name"] for f in data["features"]]
    assert "weather_temperature" in names
    assert "weather_bucket" in names
    assert "weather_is_severe" in names


@pytest.mark.anyio
async def test_catalog_entries_have_fields(client: AsyncClient):
    resp = await client.get("/pipeline/weather/catalog")
    for entry in resp.json()["features"]:
        assert "name" in entry
        assert "description" in entry
        assert "value_type" in entry
        assert "source" in entry


@pytest.mark.anyio
async def test_multiple_stations_same_hour(client: AsyncClient):
    """Each station should have features for the same hour."""
    for sid in ["station_01", "station_02", "station_03"]:
        resp = await client.get("/pipeline/weather/features", params={
            "station_id": sid,
            "hour": "2026-03-07T15:00:00Z",
        })
        assert resp.status_code == 200
        assert resp.json()["total"] == 1


@pytest.mark.anyio
async def test_seven_days_of_data(client: AsyncClient):
    """Should have 7 days * 24 hours = 168 feature sets per station."""
    resp = await client.get("/pipeline/weather/features", params={"station_id": "station_01"})
    assert resp.json()["total"] == 168


@pytest.mark.anyio
async def test_weather_is_severe_matches_bucket(client: AsyncClient):
    resp = await client.get("/pipeline/weather/features", params={"station_id": "station_03"})
    for fs in resp.json()["feature_sets"]:
        features = fs["features"]
        if features["weather_bucket"] == "storm":
            assert features["weather_is_severe"] == 1.0
        else:
            assert features["weather_is_severe"] == 0.0
