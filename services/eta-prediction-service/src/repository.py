"""
In-memory ETA prediction repository with pre-seeded data.
"""

import uuid
from datetime import datetime, timezone

from models import ETAPrediction, RoadSegment, SpeedProfile


class ETAPredictionRepository:
    """In-memory store for ETA predictions, road segments, and speed profiles."""

    def __init__(self, seed: bool = False):
        self.predictions: list[ETAPrediction] = []
        self.segments: dict[str, RoadSegment] = {}
        self.speed_profiles: list[SpeedProfile] = []
        if seed:
            self._seed()

    def _seed(self):
        now = datetime.now(timezone.utc).isoformat()

        segments = [
            RoadSegment("seg-001", "I-95 Highway", {"lat": 40.7128, "lng": -74.0060}, {"lat": 40.7580, "lng": -73.9855}, 95.0, "low", 8.5),
            RoadSegment("seg-002", "Broadway Urban", {"lat": 40.7580, "lng": -73.9855}, {"lat": 40.7831, "lng": -73.9712}, 35.0, "high", 3.2),
            RoadSegment("seg-003", "Brooklyn Bridge", {"lat": 40.7061, "lng": -73.9969}, {"lat": 40.6982, "lng": -73.9884}, 45.0, "medium", 1.8),
            RoadSegment("seg-004", "FDR Drive", {"lat": 40.7128, "lng": -74.0060}, {"lat": 40.7614, "lng": -73.9776}, 80.0, "low", 7.1),
            RoadSegment("seg-005", "Queens Blvd", {"lat": 40.7282, "lng": -73.7949}, {"lat": 40.7433, "lng": -73.9180}, 50.0, "medium", 5.6),
            RoadSegment("seg-006", "Lincoln Tunnel", {"lat": 40.7608, "lng": -74.0022}, {"lat": 40.7614, "lng": -73.9971}, 40.0, "high", 2.4),
            RoadSegment("seg-007", "Harlem River Dr", {"lat": 40.7831, "lng": -73.9712}, {"lat": 40.8296, "lng": -73.9345}, 65.0, "low", 6.3),
            RoadSegment("seg-008", "Belt Parkway", {"lat": 40.5920, "lng": -73.9875}, {"lat": 40.6501, "lng": -74.0066}, 75.0, "medium", 9.2),
        ]
        for s in segments:
            self.segments[s.id] = s

        # 24 speed profiles: 3 per segment for hours 8, 12, 18
        for seg in segments:
            base = seg.speed_kmh
            self.speed_profiles.append(SpeedProfile(seg.id, 8, base * 0.7, 5.0))
            self.speed_profiles.append(SpeedProfile(seg.id, 12, base * 0.85, 4.0))
            self.speed_profiles.append(SpeedProfile(seg.id, 18, base * 0.65, 6.0))

        predictions = [
            ETAPrediction("pred-001", "route-A", {"lat": 40.71, "lng": -74.00}, {"lat": 40.76, "lng": -73.98}, 22.5, 24.0, 0.87, "historical", {"time_of_day": "morning", "day_of_week": "monday"}, now),
            ETAPrediction("pred-002", "route-B", {"lat": 40.73, "lng": -73.99}, {"lat": 40.78, "lng": -73.97}, 15.0, 14.2, 0.92, "historical", {"time_of_day": "afternoon", "day_of_week": "wednesday"}, now),
            ETAPrediction("pred-003", "route-C", {"lat": 40.69, "lng": -73.98}, {"lat": 40.75, "lng": -73.99}, 30.0, 33.5, 0.78, "historical", {"time_of_day": "evening", "day_of_week": "friday"}, now),
            ETAPrediction("pred-004", "route-A", {"lat": 40.71, "lng": -74.00}, {"lat": 40.76, "lng": -73.98}, 20.0, None, 0.85, "segment-based", {"segments_used": 3, "total_distance_km": 12.5}, now),
            ETAPrediction("pred-005", "route-D", {"lat": 40.65, "lng": -74.00}, {"lat": 40.83, "lng": -73.94}, 45.0, None, 0.72, "segment-based", {"segments_used": 5, "total_distance_km": 22.0}, now),
            ETAPrediction("pred-006", "route-E", {"lat": 40.76, "lng": -73.97}, {"lat": 40.59, "lng": -73.99}, 55.0, None, 0.68, "graph-based", {"nodes_explored": 12, "shortest_path_km": 25.0}, now),
        ]
        self.predictions.extend(predictions)

    # ── Predictions ──

    def list_predictions(self, method: str | None = None) -> list[ETAPrediction]:
        preds = list(self.predictions)
        if method:
            preds = [p for p in preds if p.method == method]
        return preds

    def get_prediction(self, pred_id: str) -> ETAPrediction | None:
        for p in self.predictions:
            if p.id == pred_id:
                return p
        return None

    def create_prediction(self, data: dict) -> ETAPrediction:
        pred_id = f"pred-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()
        method = data.get("method", "historical")

        # Calculate predicted_minutes based on method
        if method == "historical":
            predicted = 25.0
            confidence = 0.85
            features = {"time_of_day": "current", "method": "historical_avg"}
        elif method == "segment-based":
            predicted = 30.0
            confidence = 0.80
            features = {"segments_used": 2, "total_distance_km": 10.0}
        else:  # graph-based
            predicted = 35.0
            confidence = 0.70
            features = {"nodes_explored": 8, "shortest_path_km": 15.0}

        pred = ETAPrediction(
            id=pred_id,
            route_id=data["route_id"],
            origin=data["origin"],
            destination=data["destination"],
            predicted_minutes=predicted,
            actual_minutes=None,
            confidence=confidence,
            method=method,
            features=features,
            created_at=now,
        )
        self.predictions.append(pred)
        return pred

    # ── Segments ──

    def list_segments(self) -> list[RoadSegment]:
        return list(self.segments.values())

    def get_segment(self, seg_id: str) -> RoadSegment | None:
        return self.segments.get(seg_id)

    def get_speed_profiles(self, seg_id: str) -> list[SpeedProfile]:
        return [sp for sp in self.speed_profiles if sp.segment_id == seg_id]

    def record_speed(self, seg_id: str, hour: int, speed: float) -> SpeedProfile | None:
        seg = self.segments.get(seg_id)
        if not seg:
            return None
        # Update or create speed profile
        for sp in self.speed_profiles:
            if sp.segment_id == seg_id and sp.hour == hour:
                sp.avg_speed = (sp.avg_speed + speed) / 2
                return sp
        new_sp = SpeedProfile(seg_id, hour, speed, 0.0)
        self.speed_profiles.append(new_sp)
        return new_sp

    # ── Stats ──

    def get_stats(self) -> dict:
        by_method: dict[str, int] = {}
        total_confidence = 0.0
        for p in self.predictions:
            by_method[p.method] = by_method.get(p.method, 0) + 1
            total_confidence += p.confidence
        avg_confidence = total_confidence / len(self.predictions) if self.predictions else 0.0
        return {
            "total_predictions": len(self.predictions),
            "by_method": by_method,
            "avg_confidence": round(avg_confidence, 4),
        }


REPO_CLASS = ETAPredictionRepository
repo = ETAPredictionRepository(seed=True)
