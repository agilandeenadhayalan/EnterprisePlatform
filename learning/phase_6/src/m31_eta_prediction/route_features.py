"""
Route Feature Extraction — Numeric features for ETA prediction.

WHY THIS MATTERS:
Machine learning models need numeric features. This module extracts
meaningful features from a route (list of road segments) that capture
distance, road composition, time-of-day effects, and congestion state.

Key concepts:
  - Total distance: sum of segment lengths.
  - Road type distribution: fraction of highway vs. urban vs. residential.
  - Time-of-day encoding: sine/cosine encoding of the hour, capturing the
    cyclical nature of time (hour 23 is close to hour 0).
  - Congestion ratio: fraction of segments experiencing moderate or worse
    congestion, a proxy for overall route quality.
"""

import math

from .road_network import RoadNetwork, CongestionLevel


class RouteFeatureExtractor:
    """Extract numeric features from a route for use in ETA models.

    A route is a list of segment IDs. The extractor uses the road network
    to look up segment attributes and compute aggregate features.
    """

    def __init__(self, road_network: RoadNetwork):
        self._network = road_network

    def total_distance(self, segments: list[str]) -> float:
        """Sum of distances across all segments in km."""
        total = 0.0
        for seg_id in segments:
            seg = self._network.get_segment(seg_id)
            total += seg.distance_km
        return total

    def num_turns(self, segments: list[str]) -> int:
        """Count direction changes in the route.

        A turn is detected when consecutive segments have different road
        types (e.g., switching from highway to urban). This is a
        simplification — real systems use bearing angles.
        """
        if len(segments) <= 1:
            return 0
        turns = 0
        for i in range(1, len(segments)):
            prev_seg = self._network.get_segment(segments[i - 1])
            curr_seg = self._network.get_segment(segments[i])
            if prev_seg.road_type != curr_seg.road_type:
                turns += 1
        return turns

    def road_type_distribution(self, segments: list[str]) -> dict:
        """Fraction of the route on each road type.

        Returns a dict like {"highway": 0.6, "urban": 0.4}. The fractions
        are by count of segments, not by distance.
        """
        if not segments:
            return {}
        type_counts: dict[str, int] = {}
        for seg_id in segments:
            seg = self._network.get_segment(seg_id)
            type_counts[seg.road_type] = type_counts.get(seg.road_type, 0) + 1
        total = len(segments)
        return {rt: count / total for rt, count in type_counts.items()}

    def time_of_day_features(self, hour: int) -> dict:
        """Sine/cosine encoding of the hour.

        Cyclical encoding ensures that hour 23 is close to hour 0 in
        feature space. This is critical for ML models — without it, the
        model would think midnight and 11 PM are far apart.

        Returns {"hour_sin": sin(2*pi*hour/24), "hour_cos": cos(2*pi*hour/24)}.
        """
        angle = 2 * math.pi * hour / 24.0
        return {
            "hour_sin": math.sin(angle),
            "hour_cos": math.cos(angle),
        }

    def congestion_ratio(self, segments: list[str], hour: int) -> float:
        """Fraction of segments with MODERATE or worse congestion.

        Uses speed profiles for the given hour to determine each segment's
        effective speed, then checks congestion level.
        """
        if not segments:
            return 0.0
        congested_count = 0
        congested_levels = {
            CongestionLevel.MODERATE,
            CongestionLevel.HEAVY,
            CongestionLevel.GRIDLOCK,
        }
        for seg_id in segments:
            speed = self._network._get_speed_for_segment(seg_id, hour)
            level = self._network.get_congestion(seg_id, speed)
            if level in congested_levels:
                congested_count += 1
        return congested_count / len(segments)

    def extract_all(self, segments: list[str], hour: int) -> dict:
        """Extract all features into a single dict.

        Combines distance, turns, road type distribution, time-of-day
        encoding, and congestion ratio into one feature vector suitable
        for ML model input.
        """
        features = {
            "total_distance": self.total_distance(segments),
            "num_turns": self.num_turns(segments),
            "congestion_ratio": self.congestion_ratio(segments, hour),
        }
        features.update(self.time_of_day_features(hour))
        features.update(self.road_type_distribution(segments))
        return features
