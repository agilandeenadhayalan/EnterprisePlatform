"""
Tests for ETL Worker Weather Loader service.

Covers weather data loading, status tracking, station listing,
date validation, and unit conversion logic.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "Weather Loader" in data["service"]


@pytest.mark.anyio
async def test_load_weather_data(client: AsyncClient):
    response = await client.post("/load", json={
        "start_date": "2023-01-01",
        "end_date": "2023-01-31",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["state"] == "completed"
    assert data["rows_loaded"] > 0
    assert data["stations_processed"] > 0
    assert data["start_date"] == "2023-01-01"
    assert data["end_date"] == "2023-01-31"


@pytest.mark.anyio
async def test_load_weather_specific_stations(client: AsyncClient):
    response = await client.post("/load", json={
        "start_date": "2023-06-01",
        "end_date": "2023-06-30",
        "station_ids": ["USW00094728", "USW00014732"],
    })
    assert response.status_code == 200
    data = response.json()
    assert data["state"] == "completed"
    assert data["stations_processed"] == 2


@pytest.mark.anyio
async def test_load_weather_invalid_date_range(client: AsyncClient):
    response = await client.post("/load", json={
        "start_date": "2023-12-31",
        "end_date": "2023-01-01",
    })
    assert response.status_code == 400


@pytest.mark.anyio
async def test_load_weather_single_day(client: AsyncClient):
    response = await client.post("/load", json={
        "start_date": "2023-07-04",
        "end_date": "2023-07-04",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["state"] == "completed"


@pytest.mark.anyio
async def test_load_status(client: AsyncClient):
    await client.post("/load", json={
        "start_date": "2023-03-01",
        "end_date": "2023-03-31",
    })

    response = await client.get("/load/status")
    assert response.status_code == 200
    data = response.json()
    assert "active_jobs" in data
    assert "completed_jobs" in data
    assert "total_rows_loaded" in data
    assert data["completed_jobs"] >= 1
    assert data["total_rows_loaded"] > 0


@pytest.mark.anyio
async def test_list_stations(client: AsyncClient):
    response = await client.get("/stations")
    assert response.status_code == 200
    data = response.json()
    assert "stations" in data
    assert "total" in data
    assert data["total"] >= 5
    station_ids = [s["station_id"] for s in data["stations"]]
    assert "USW00094728" in station_ids  # Central Park


@pytest.mark.anyio
async def test_station_details(client: AsyncClient):
    response = await client.get("/stations")
    data = response.json()
    central_park = next(s for s in data["stations"] if s["station_id"] == "USW00094728")
    assert central_park["name"] == "NY CITY CENTRAL PARK"
    assert central_park["state"] == "NY"
    assert central_park["country"] == "US"
    assert central_park["latitude"] > 0
    assert central_park["longitude"] < 0


@pytest.mark.anyio
async def test_load_job_has_timestamps(client: AsyncClient):
    response = await client.post("/load", json={
        "start_date": "2023-08-01",
        "end_date": "2023-08-31",
    })
    data = response.json()
    assert data["started_at"] is not None
    assert data["completed_at"] is not None


@pytest.mark.anyio
async def test_celsius_to_fahrenheit_conversion():
    """Test unit conversion logic in WeatherRecord model."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from models import WeatherRecord

    assert abs(WeatherRecord.celsius_to_fahrenheit(0) - 32.0) < 0.01
    assert abs(WeatherRecord.celsius_to_fahrenheit(100) - 212.0) < 0.01
    assert abs(WeatherRecord.celsius_to_fahrenheit(-40) - (-40.0)) < 0.01


@pytest.mark.anyio
async def test_fahrenheit_to_celsius_conversion():
    """Test reverse unit conversion logic."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from models import WeatherRecord

    assert abs(WeatherRecord.fahrenheit_to_celsius(32) - 0.0) < 0.01
    assert abs(WeatherRecord.fahrenheit_to_celsius(212) - 100.0) < 0.01
