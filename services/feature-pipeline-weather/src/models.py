"""
Domain models for the Feature Pipeline Weather service.
"""


class WeatherFeatureSet:
    """Computed weather features for a station at a given hour."""

    def __init__(
        self,
        station_id: str,
        hour: str,
        features: dict,
        computed_at: str = "2026-03-09T12:00:00Z",
    ):
        self.station_id = station_id
        self.hour = hour
        self.features = features
        self.computed_at = computed_at

    def to_dict(self) -> dict:
        return {
            "station_id": self.station_id,
            "hour": self.hour,
            "features": self.features,
            "computed_at": self.computed_at,
        }


class WeatherBucket:
    """Weather condition bucket classification."""

    CLEAR = "clear"
    RAIN = "rain"
    SNOW = "snow"
    FOG = "fog"
    STORM = "storm"

    ALL_BUCKETS = [CLEAR, RAIN, SNOW, FOG, STORM]

    @staticmethod
    def classify(temperature: float, precipitation: float, visibility: float, wind_speed: float) -> str:
        """Classify weather conditions into a bucket."""
        if wind_speed > 60 or precipitation > 20:
            return WeatherBucket.STORM
        if precipitation > 5 and temperature <= 0:
            return WeatherBucket.SNOW
        if precipitation > 2:
            return WeatherBucket.RAIN
        if visibility < 2:
            return WeatherBucket.FOG
        return WeatherBucket.CLEAR
