"""
In-memory feature store repository with pre-seeded data.
"""

from models import FeatureDefinition, FeatureValue, FeatureVector


class FeatureStoreRepository:
    """In-memory store for feature definitions and values."""

    def __init__(self, seed: bool = False):
        self.definitions: dict[str, FeatureDefinition] = {}
        self.values: list[FeatureValue] = []
        if seed:
            self._seed()

    def _seed(self):
        defs = [
            FeatureDefinition("driver_avg_rating", "driver", "float", "rides-db", "Average driver rating over all trips", 1800),
            FeatureDefinition("driver_total_trips_30d", "driver", "int", "rides-db", "Total trips completed in last 30 days", 3600),
            FeatureDefinition("driver_earnings_per_hour", "driver", "float", "payments-db", "Average earnings per online hour", 3600),
            FeatureDefinition("driver_acceptance_rate", "driver", "float", "rides-db", "Rate of accepted ride requests", 1800),
            FeatureDefinition("driver_cancel_rate", "driver", "float", "rides-db", "Rate of cancelled rides after acceptance", 1800),
            FeatureDefinition("zone_demand_last_hour", "zone", "int", "rides-db", "Number of ride requests in zone in last hour", 300),
            FeatureDefinition("zone_avg_fare", "zone", "float", "rides-db", "Average fare for rides starting in zone", 1800),
            FeatureDefinition("zone_avg_wait_time", "zone", "float", "rides-db", "Average wait time for riders in zone (seconds)", 600),
            FeatureDefinition("zone_supply_density", "zone", "float", "driver-location", "Number of available drivers per sq km in zone", 300),
            FeatureDefinition("zone_surge_factor", "zone", "float", "pricing-engine", "Current surge pricing multiplier for zone", 60),
            FeatureDefinition("weather_temperature", "location", "float", "weather-api", "Current temperature in Celsius", 900),
            FeatureDefinition("weather_precipitation", "location", "float", "weather-api", "Precipitation in mm/hr", 900),
            FeatureDefinition("weather_wind_speed", "location", "float", "weather-api", "Wind speed in km/h", 900),
            FeatureDefinition("weather_visibility", "location", "float", "weather-api", "Visibility in kilometers", 900),
            FeatureDefinition("weather_is_severe", "location", "bool", "weather-api", "Whether severe weather alert is active", 300),
        ]
        for d in defs:
            self.definitions[d.name] = d

        seed_values = [
            FeatureValue("driver_001", "driver_avg_rating", 4.85, "2026-03-09T11:00:00Z"),
            FeatureValue("driver_001", "driver_total_trips_30d", 142.0, "2026-03-09T11:00:00Z"),
            FeatureValue("driver_001", "driver_earnings_per_hour", 28.50, "2026-03-09T11:00:00Z"),
            FeatureValue("driver_001", "driver_acceptance_rate", 0.92, "2026-03-09T11:00:00Z"),
            FeatureValue("driver_001", "driver_cancel_rate", 0.03, "2026-03-09T11:00:00Z"),
            FeatureValue("driver_002", "driver_avg_rating", 4.72, "2026-03-09T11:00:00Z"),
            FeatureValue("driver_002", "driver_total_trips_30d", 98.0, "2026-03-09T11:00:00Z"),
            FeatureValue("driver_002", "driver_earnings_per_hour", 24.10, "2026-03-09T11:00:00Z"),
            FeatureValue("zone_A1", "zone_demand_last_hour", 47.0, "2026-03-09T12:00:00Z"),
            FeatureValue("zone_A1", "zone_avg_fare", 18.30, "2026-03-09T12:00:00Z"),
            FeatureValue("zone_A1", "zone_avg_wait_time", 240.0, "2026-03-09T12:00:00Z"),
            FeatureValue("zone_A1", "zone_supply_density", 3.2, "2026-03-09T12:00:00Z"),
            FeatureValue("zone_A1", "zone_surge_factor", 1.4, "2026-03-09T12:00:00Z"),
            FeatureValue("station_01", "weather_temperature", 22.5, "2026-03-09T12:00:00Z"),
            FeatureValue("station_01", "weather_precipitation", 0.0, "2026-03-09T12:00:00Z"),
            FeatureValue("station_01", "weather_wind_speed", 12.3, "2026-03-09T12:00:00Z"),
            FeatureValue("station_01", "weather_visibility", 15.0, "2026-03-09T12:00:00Z"),
            FeatureValue("station_01", "weather_is_severe", 0.0, "2026-03-09T12:00:00Z"),
        ]
        self.values.extend(seed_values)

    # ── Definitions ──

    def list_definitions(self) -> list[FeatureDefinition]:
        return list(self.definitions.values())

    def get_definition(self, name: str) -> FeatureDefinition | None:
        return self.definitions.get(name)

    def create_definition(self, data: dict) -> FeatureDefinition:
        fd = FeatureDefinition(**data)
        self.definitions[fd.name] = fd
        return fd

    # ── Online / Offline ──

    def get_online_features(self, entity_id: str, feature_names: list[str]) -> FeatureVector:
        features = {}
        for fv in self.values:
            if fv.entity_id == entity_id and fv.feature_name in feature_names:
                features[fv.feature_name] = fv.value
        return FeatureVector(entity_id=entity_id, features=features)

    def get_offline_features(self, entity_ids: list[str], feature_names: list[str]) -> list[FeatureVector]:
        vectors = []
        for eid in entity_ids:
            vec = self.get_online_features(eid, feature_names)
            vectors.append(vec)
        return vectors

    # ── Ingest ──

    def ingest_value(self, entity_id: str, feature_name: str, value: float, timestamp: str | None = None) -> FeatureValue:
        ts = timestamp or "2026-03-09T12:00:00Z"
        fv = FeatureValue(entity_id=entity_id, feature_name=feature_name, value=value, timestamp=ts)
        self.values.append(fv)
        return fv

    # ── Stats ──

    def get_stats(self) -> dict:
        entity_types = list({d.entity_type for d in self.definitions.values()})
        sources = list({d.source for d in self.definitions.values()})
        return {
            "total_definitions": len(self.definitions),
            "active_definitions": sum(1 for d in self.definitions.values() if d.is_active),
            "total_values": len(self.values),
            "entity_types": sorted(entity_types),
            "sources": sorted(sources),
        }


REPO_CLASS = FeatureStoreRepository
repo = FeatureStoreRepository(seed=True)
