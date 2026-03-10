"""
Domain models for the Demand Forecast service.
"""


class DemandForecast:
    """A demand forecast record."""

    def __init__(
        self,
        id: str,
        zone_id: str,
        time_slot: str,
        predicted_demand: float,
        actual_demand: float | None,
        uncertainty_low: float,
        uncertainty_high: float,
        method: str,
        weather_factor: float,
        created_at: str = "2026-03-01T00:00:00Z",
    ):
        self.id = id
        self.zone_id = zone_id
        self.time_slot = time_slot
        self.predicted_demand = predicted_demand
        self.actual_demand = actual_demand
        self.uncertainty_low = uncertainty_low
        self.uncertainty_high = uncertainty_high
        self.method = method
        self.weather_factor = weather_factor
        self.created_at = created_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "zone_id": self.zone_id,
            "time_slot": self.time_slot,
            "predicted_demand": self.predicted_demand,
            "actual_demand": self.actual_demand,
            "uncertainty_low": self.uncertainty_low,
            "uncertainty_high": self.uncertainty_high,
            "method": self.method,
            "weather_factor": self.weather_factor,
            "created_at": self.created_at,
        }


class GridCell:
    """A geographic grid cell / zone."""

    def __init__(
        self,
        id: str,
        zone_name: str,
        lat: float,
        lng: float,
        base_demand: float,
    ):
        self.id = id
        self.zone_name = zone_name
        self.lat = lat
        self.lng = lng
        self.base_demand = base_demand

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "zone_name": self.zone_name,
            "lat": self.lat,
            "lng": self.lng,
            "base_demand": self.base_demand,
        }


class WeatherImpact:
    """Weather condition impact on demand."""

    def __init__(
        self,
        condition: str,
        impact_coefficient: float,
    ):
        self.condition = condition
        self.impact_coefficient = impact_coefficient

    def to_dict(self) -> dict:
        return {
            "condition": self.condition,
            "impact_coefficient": self.impact_coefficient,
        }
