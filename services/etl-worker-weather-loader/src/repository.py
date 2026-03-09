"""
In-memory repository for ETL Worker Weather Loader service.

Manages weather stations, load jobs, and data tracking for NOAA
weather data loading into ClickHouse dim_weather table.
"""

import uuid
from datetime import date, datetime
from typing import Optional

from models import LoadJob, LoadState, WeatherStation


# NYC-area NOAA weather stations
DEFAULT_STATIONS = [
    WeatherStation(
        station_id="USW00094728",
        name="NY CITY CENTRAL PARK",
        latitude=40.7789,
        longitude=-73.9692,
        elevation_m=42.7,
        state="NY",
    ),
    WeatherStation(
        station_id="USW00014732",
        name="LAGUARDIA AIRPORT",
        latitude=40.7794,
        longitude=-73.88,
        elevation_m=3.4,
        state="NY",
    ),
    WeatherStation(
        station_id="USW00094789",
        name="JFK INTERNATIONAL AIRPORT",
        latitude=40.6386,
        longitude=-73.7622,
        elevation_m=3.4,
        state="NY",
    ),
    WeatherStation(
        station_id="USW00014734",
        name="NEWARK LIBERTY INTL AP",
        latitude=40.6833,
        longitude=-74.1694,
        elevation_m=2.1,
        state="NJ",
    ),
    WeatherStation(
        station_id="USC00305801",
        name="NEW YORK AVE V BROOKLYN",
        latitude=40.5981,
        longitude=-73.9544,
        elevation_m=4.6,
        state="NY",
    ),
]


class WeatherLoaderRepository:
    def __init__(self):
        self._jobs: dict[str, LoadJob] = {}
        self._stations: dict[str, WeatherStation] = {}
        self._init_default_stations()

    def _init_default_stations(self):
        for station in DEFAULT_STATIONS:
            self._stations[station.station_id] = station

    def create_load_job(self, start_date: date, end_date: date) -> LoadJob:
        job_id = str(uuid.uuid4())
        job = LoadJob(
            job_id=job_id,
            start_date=start_date,
            end_date=end_date,
            state=LoadState.RUNNING,
            started_at=datetime.utcnow(),
        )
        self._jobs[job_id] = job
        return job

    def complete_job(
        self, job_id: str, rows_loaded: int, stations_processed: int
    ) -> Optional[LoadJob]:
        job = self._jobs.get(job_id)
        if not job:
            return None
        job.state = LoadState.COMPLETED
        job.rows_loaded = rows_loaded
        job.stations_processed = stations_processed
        job.completed_at = datetime.utcnow()
        return job

    def fail_job(self, job_id: str, error_message: str) -> Optional[LoadJob]:
        job = self._jobs.get(job_id)
        if not job:
            return None
        job.state = LoadState.FAILED
        job.error_message = error_message
        job.completed_at = datetime.utcnow()
        return job

    def get_job(self, job_id: str) -> Optional[LoadJob]:
        return self._jobs.get(job_id)

    def get_all_jobs(self) -> list[LoadJob]:
        return list(self._jobs.values())

    def get_active_jobs(self) -> list[LoadJob]:
        return [j for j in self._jobs.values() if j.state == LoadState.RUNNING]

    def get_completed_jobs(self) -> list[LoadJob]:
        return [j for j in self._jobs.values() if j.state == LoadState.COMPLETED]

    def get_total_rows_loaded(self) -> int:
        return sum(j.rows_loaded for j in self._jobs.values() if j.state == LoadState.COMPLETED)

    def get_all_stations(self) -> list[WeatherStation]:
        return list(self._stations.values())

    def get_station(self, station_id: str) -> Optional[WeatherStation]:
        return self._stations.get(station_id)

    def get_station_count(self) -> int:
        return len(self._stations)


# Singleton
weather_loader_repo = WeatherLoaderRepository()
