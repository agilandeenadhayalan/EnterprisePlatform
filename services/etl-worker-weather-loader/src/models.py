"""
Domain models for ETL Worker Weather Loader service.

Represents NOAA weather data records, weather stations, and loading
jobs for populating ClickHouse dim_weather table.
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional


class LoadState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class WeatherRecord:
    """A single NOAA weather observation mapped to dim_weather."""

    def __init__(
        self,
        station_id: str,
        observation_date: date,
        temp_celsius: Optional[float] = None,
        temp_fahrenheit: Optional[float] = None,
        precipitation_mm: Optional[float] = None,
        wind_speed_kmh: Optional[float] = None,
        humidity_percent: Optional[float] = None,
        weather_condition: Optional[str] = None,
    ):
        self.station_id = station_id
        self.observation_date = observation_date
        self.temp_celsius = temp_celsius
        self.temp_fahrenheit = temp_fahrenheit or (
            (temp_celsius * 9 / 5 + 32) if temp_celsius is not None else None
        )
        self.precipitation_mm = precipitation_mm
        self.wind_speed_kmh = wind_speed_kmh
        self.humidity_percent = humidity_percent
        self.weather_condition = weather_condition

    @staticmethod
    def celsius_to_fahrenheit(celsius: float) -> float:
        return celsius * 9.0 / 5.0 + 32.0

    @staticmethod
    def fahrenheit_to_celsius(fahrenheit: float) -> float:
        return (fahrenheit - 32.0) * 5.0 / 9.0


class WeatherStation:
    def __init__(
        self,
        station_id: str,
        name: str,
        latitude: float,
        longitude: float,
        elevation_m: Optional[float] = None,
        state: Optional[str] = None,
        country: str = "US",
    ):
        self.station_id = station_id
        self.name = name
        self.latitude = latitude
        self.longitude = longitude
        self.elevation_m = elevation_m
        self.state = state
        self.country = country


class LoadJob:
    def __init__(
        self,
        job_id: str,
        start_date: date,
        end_date: date,
        state: LoadState = LoadState.PENDING,
        rows_loaded: int = 0,
        stations_processed: int = 0,
        error_message: Optional[str] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
    ):
        self.job_id = job_id
        self.start_date = start_date
        self.end_date = end_date
        self.state = state
        self.rows_loaded = rows_loaded
        self.stations_processed = stations_processed
        self.error_message = error_message
        self.started_at = started_at or datetime.utcnow()
        self.completed_at = completed_at
