"""
Domain models for the Feature Pipeline Zone service.
"""


class ZoneFeatureSet:
    """Computed feature set for a zone at a given hour."""

    def __init__(
        self,
        zone_id: str,
        hour: str,
        features: dict,
        computed_at: str = "2026-03-09T12:00:00Z",
    ):
        self.zone_id = zone_id
        self.hour = hour
        self.features = features
        self.computed_at = computed_at

    def to_dict(self) -> dict:
        return {
            "zone_id": self.zone_id,
            "hour": self.hour,
            "features": self.features,
            "computed_at": self.computed_at,
        }
