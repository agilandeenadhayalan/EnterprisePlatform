"""
In-memory demand forecast repository with pre-seeded data.
"""

import uuid
from datetime import datetime, timezone

from models import DemandForecast, GridCell, WeatherImpact


class DemandForecastRepository:
    """In-memory store for demand forecasts, grid cells, and weather impacts."""

    def __init__(self, seed: bool = False):
        self.forecasts: list[DemandForecast] = []
        self.zones: dict[str, GridCell] = {}
        self.weather_impacts: dict[str, WeatherImpact] = {}
        if seed:
            self._seed()

    def _seed(self):
        now = datetime.now(timezone.utc).isoformat()

        zones = [
            GridCell("zone-001", "manhattan_midtown", 40.7549, -73.9840, 120.0),
            GridCell("zone-002", "manhattan_downtown", 40.7128, -74.0060, 95.0),
            GridCell("zone-003", "brooklyn_heights", 40.6960, -73.9936, 60.0),
            GridCell("zone-004", "williamsburg", 40.7081, -73.9571, 55.0),
            GridCell("zone-005", "astoria", 40.7720, -73.9303, 45.0),
            GridCell("zone-006", "upper_east_side", 40.7736, -73.9566, 80.0),
            GridCell("zone-007", "harlem", 40.8116, -73.9465, 50.0),
            GridCell("zone-008", "chelsea", 40.7465, -74.0014, 70.0),
            GridCell("zone-009", "soho", 40.7233, -73.9987, 85.0),
            GridCell("zone-010", "flushing", 40.7580, -73.8317, 40.0),
        ]
        for z in zones:
            self.zones[z.id] = z

        weather = [
            WeatherImpact("clear", 1.0),
            WeatherImpact("rain", 0.7),
            WeatherImpact("snow", 0.4),
            WeatherImpact("heat", 0.85),
            WeatherImpact("storm", 0.3),
        ]
        for w in weather:
            self.weather_impacts[w.condition] = w

        forecasts = [
            DemandForecast("fc-001", "zone-001", "2026-03-10T08:00", 108.0, 112.0, 90.0, 126.0, "time_series", 0.9, now),
            DemandForecast("fc-002", "zone-001", "2026-03-10T12:00", 96.0, 98.0, 80.0, 112.0, "time_series", 0.8, now),
            DemandForecast("fc-003", "zone-002", "2026-03-10T08:00", 85.5, 80.0, 70.0, 101.0, "time_series", 0.9, now),
            DemandForecast("fc-004", "zone-003", "2026-03-10T18:00", 42.0, None, 30.0, 54.0, "regression", 0.7, now),
            DemandForecast("fc-005", "zone-004", "2026-03-10T08:00", 49.5, None, 38.0, 61.0, "regression", 0.9, now),
            DemandForecast("fc-006", "zone-005", "2026-03-10T12:00", 38.25, None, 28.0, 48.5, "neural_network", 0.85, now),
            DemandForecast("fc-007", "zone-006", "2026-03-10T18:00", 56.0, 60.0, 44.0, 68.0, "neural_network", 0.7, now),
            DemandForecast("fc-008", "zone-007", "2026-03-10T08:00", 20.0, None, 12.0, 28.0, "ensemble", 0.4, now),
        ]
        self.forecasts.extend(forecasts)

    # ── Forecasts ──

    def list_forecasts(self, zone_id: str | None = None, method: str | None = None) -> list[DemandForecast]:
        result = list(self.forecasts)
        if zone_id:
            result = [f for f in result if f.zone_id == zone_id]
        if method:
            result = [f for f in result if f.method == method]
        return result

    def get_forecast(self, fc_id: str) -> DemandForecast | None:
        for f in self.forecasts:
            if f.id == fc_id:
                return f
        return None

    def create_forecast(self, data: dict) -> DemandForecast:
        fc_id = f"fc-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()
        zone = self.zones.get(data["zone_id"])
        base = zone.base_demand if zone else 50.0

        # Use first weather impact as default
        weather_factor = 1.0
        if self.weather_impacts:
            weather_factor = list(self.weather_impacts.values())[0].impact_coefficient

        predicted = base * weather_factor
        uncertainty_low = predicted * 0.8
        uncertainty_high = predicted * 1.2

        fc = DemandForecast(
            id=fc_id,
            zone_id=data["zone_id"],
            time_slot=data["time_slot"],
            predicted_demand=predicted,
            actual_demand=None,
            uncertainty_low=round(uncertainty_low, 2),
            uncertainty_high=round(uncertainty_high, 2),
            method=data.get("method", "time_series"),
            weather_factor=weather_factor,
            created_at=now,
        )
        self.forecasts.append(fc)
        return fc

    # ── Zones ──

    def list_zones(self) -> list[GridCell]:
        return list(self.zones.values())

    def get_zone(self, zone_id: str) -> GridCell | None:
        return self.zones.get(zone_id)

    # ── Weather ──

    def upsert_weather_impact(self, condition: str, coefficient: float) -> WeatherImpact:
        wi = WeatherImpact(condition, coefficient)
        self.weather_impacts[condition] = wi
        return wi

    # ── Stats ──

    def get_stats(self) -> dict:
        by_method: dict[str, int] = {}
        total_range = 0.0
        for f in self.forecasts:
            by_method[f.method] = by_method.get(f.method, 0) + 1
            total_range += f.uncertainty_high - f.uncertainty_low
        avg_range = total_range / len(self.forecasts) if self.forecasts else 0.0
        return {
            "total_forecasts": len(self.forecasts),
            "by_method": by_method,
            "avg_uncertainty_range": round(avg_range, 4),
        }


REPO_CLASS = DemandForecastRepository
repo = DemandForecastRepository(seed=True)
