"""
Domain models for the ETA Prediction service.
"""


class ETAPrediction:
    """An ETA prediction record."""

    def __init__(
        self,
        id: str,
        route_id: str,
        origin: dict,
        destination: dict,
        predicted_minutes: float,
        actual_minutes: float | None,
        confidence: float,
        method: str,
        features: dict,
        created_at: str = "2026-03-01T00:00:00Z",
    ):
        self.id = id
        self.route_id = route_id
        self.origin = origin
        self.destination = destination
        self.predicted_minutes = predicted_minutes
        self.actual_minutes = actual_minutes
        self.confidence = confidence
        self.method = method
        self.features = features
        self.created_at = created_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "route_id": self.route_id,
            "origin": self.origin,
            "destination": self.destination,
            "predicted_minutes": self.predicted_minutes,
            "actual_minutes": self.actual_minutes,
            "confidence": self.confidence,
            "method": self.method,
            "features": self.features,
            "created_at": self.created_at,
        }


class RoadSegment:
    """A road segment with speed and congestion data."""

    def __init__(
        self,
        id: str,
        name: str,
        start_point: dict,
        end_point: dict,
        speed_kmh: float,
        congestion_level: str,
        distance_km: float,
    ):
        self.id = id
        self.name = name
        self.start_point = start_point
        self.end_point = end_point
        self.speed_kmh = speed_kmh
        self.congestion_level = congestion_level
        self.distance_km = distance_km

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "start_point": self.start_point,
            "end_point": self.end_point,
            "speed_kmh": self.speed_kmh,
            "congestion_level": self.congestion_level,
            "distance_km": self.distance_km,
        }


class SpeedProfile:
    """Speed profile for a road segment at a given hour."""

    def __init__(
        self,
        segment_id: str,
        hour: int,
        avg_speed: float,
        stddev: float,
    ):
        self.segment_id = segment_id
        self.hour = hour
        self.avg_speed = avg_speed
        self.stddev = stddev

    def to_dict(self) -> dict:
        return {
            "segment_id": self.segment_id,
            "hour": self.hour,
            "avg_speed": self.avg_speed,
            "stddev": self.stddev,
        }
