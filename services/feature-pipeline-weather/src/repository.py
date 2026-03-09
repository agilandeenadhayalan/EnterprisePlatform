"""
In-memory repository for the Weather Feature Pipeline service with pre-seeded data.
"""

import uuid

from models import WeatherFeatureSet, WeatherBucket


WEATHER_FEATURE_CATALOG = [
    {"name": "weather_temperature", "description": "Current temperature in Celsius", "value_type": "float", "source": "weather-api"},
    {"name": "weather_precipitation", "description": "Precipitation in mm/hr", "value_type": "float", "source": "weather-api"},
    {"name": "weather_wind_speed", "description": "Wind speed in km/h", "value_type": "float", "source": "weather-api"},
    {"name": "weather_visibility", "description": "Visibility in kilometers", "value_type": "float", "source": "weather-api"},
    {"name": "weather_humidity", "description": "Relative humidity percentage", "value_type": "float", "source": "weather-api"},
    {"name": "weather_pressure", "description": "Atmospheric pressure in hPa", "value_type": "float", "source": "weather-api"},
    {"name": "weather_bucket", "description": "Weather condition bucket (clear/rain/snow/fog/storm)", "value_type": "str", "source": "weather-api"},
    {"name": "weather_is_severe", "description": "Whether severe weather alert is active", "value_type": "bool", "source": "weather-api"},
]


class WeatherPipelineRepository:
    """In-memory store for weather feature pipeline."""

    def __init__(self, seed: bool = False):
        self.feature_sets: list[WeatherFeatureSet] = []
        self.runs: list[dict] = []
        if seed:
            self._seed()

    def _seed(self):
        import random
        random.seed(42)

        stations = [f"station_{i:02d}" for i in range(1, 6)]
        # 7 days, 24 hours each
        for day in range(3, 10):
            for hour_num in range(0, 24):
                hour_str = f"2026-03-{day:02d}T{hour_num:02d}:00:00Z"
                for station_id in stations:
                    temp = round(random.uniform(-5.0, 35.0), 1)
                    precip = round(random.uniform(0.0, 15.0), 1)
                    wind = round(random.uniform(0.0, 50.0), 1)
                    vis = round(random.uniform(1.0, 20.0), 1)
                    humidity = round(random.uniform(20.0, 100.0), 1)
                    pressure = round(random.uniform(990.0, 1040.0), 1)
                    bucket = WeatherBucket.classify(temp, precip, vis, wind)
                    is_severe = 1.0 if bucket == WeatherBucket.STORM else 0.0

                    features = {
                        "weather_temperature": temp,
                        "weather_precipitation": precip,
                        "weather_wind_speed": wind,
                        "weather_visibility": vis,
                        "weather_humidity": humidity,
                        "weather_pressure": pressure,
                        "weather_bucket": bucket,
                        "weather_is_severe": is_severe,
                    }
                    self.feature_sets.append(
                        WeatherFeatureSet(
                            station_id=station_id,
                            hour=hour_str,
                            features=features,
                            computed_at=hour_str,
                        )
                    )

    # ── Pipeline ──

    def run_pipeline(self, station_ids: list[str] | None = None) -> dict:
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        targets = station_ids or [f"station_{i:02d}" for i in range(1, 6)]
        run = {
            "id": run_id,
            "status": "completed",
            "start_time": "2026-03-09T12:00:00Z",
            "end_time": "2026-03-09T12:02:15Z",
            "features_computed": len(targets) * len(WEATHER_FEATURE_CATALOG),
        }
        self.runs.append(run)
        return run

    # ── Features ──

    def get_features(self, station_id: str, hour: str | None = None) -> list[WeatherFeatureSet]:
        results = [fs for fs in self.feature_sets if fs.station_id == station_id]
        if hour:
            results = [fs for fs in results if fs.hour == hour]
        return results

    def get_latest_features(self, station_id: str) -> WeatherFeatureSet | None:
        matches = [fs for fs in self.feature_sets if fs.station_id == station_id]
        return matches[-1] if matches else None

    # ── Catalog ──

    def get_catalog(self) -> list[dict]:
        return WEATHER_FEATURE_CATALOG


REPO_CLASS = WeatherPipelineRepository
repo = WeatherPipelineRepository(seed=True)
