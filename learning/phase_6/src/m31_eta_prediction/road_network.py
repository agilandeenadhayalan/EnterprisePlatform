"""
Road Network Modeling — Segments, intersections, congestion, and routing.

WHY THIS MATTERS:
ETA prediction systems need an accurate model of the road network. This
module represents roads as directed graph edges connecting intersections,
with congestion levels derived from comparing current speeds to limits.
Dijkstra's algorithm finds shortest paths by distance or by estimated
travel time using hour-specific speed profiles.

Key concepts:
  - RoadSegment: a stretch of road with physical attributes.
  - SpeedProfile: how average speed varies by hour for a segment.
  - CongestionLevel: categorical congestion from FREE_FLOW to GRIDLOCK.
  - RoadNetwork: the full road graph with two flavors of shortest path.
"""

import heapq
from enum import Enum


class CongestionLevel(Enum):
    """Traffic congestion categories.

    Derived from the ratio of current speed to the segment's speed limit.
    Production systems like Google Maps use similar buckets, often color-
    coded on the map (green -> red).
    """
    FREE_FLOW = "free_flow"
    LIGHT = "light"
    MODERATE = "moderate"
    HEAVY = "heavy"
    GRIDLOCK = "gridlock"


class RoadSegment:
    """A road segment with physical attributes.

    Represents a single stretch of road between two intersections.
    Travel time is computed from distance and speed: time = distance / speed * 60.
    """

    def __init__(
        self,
        id: str,
        name: str,
        distance_km: float,
        lanes: int,
        speed_limit_kmh: float,
        road_type: str = "urban",
    ):
        self.id = id
        self.name = name
        self.distance_km = distance_km
        self.lanes = lanes
        self.speed_limit_kmh = speed_limit_kmh
        self.road_type = road_type

    def get_travel_time(self, speed_kmh: float) -> float:
        """Return travel time in minutes at the given speed.

        If speed is zero or negative, raises ValueError to avoid
        division by zero — a vehicle not moving means infinite time.
        """
        if speed_kmh <= 0:
            raise ValueError(f"Speed must be positive, got {speed_kmh}")
        return (self.distance_km / speed_kmh) * 60.0


class SpeedProfile:
    """Average speed on a road segment at a specific hour of the day.

    Speed profiles capture the time-of-day variation in traffic. For
    example, a highway segment might average 100 km/h at 3 AM but only
    30 km/h at 8 AM during rush hour.
    """

    def __init__(self, segment_id: str, hour: int, avg_speed: float, stddev: float = 0.0):
        if not 0 <= hour <= 23:
            raise ValueError(f"Hour must be 0-23, got {hour}")
        self.segment_id = segment_id
        self.hour = hour
        self.avg_speed = avg_speed
        self.stddev = stddev


class Intersection:
    """A road junction connecting multiple road segments.

    In the road network graph, intersections are nodes and road segments
    are edges. The connected_segments list stores segment IDs that meet
    at this intersection.
    """

    def __init__(self, id: str, name: str, connected_segments: list[str] = None):
        self.id = id
        self.name = name
        self.connected_segments = connected_segments or []


class RoadNetwork:
    """A road network modeled as a directed graph of intersections and segments.

    Intersections are nodes, road segments are edges. The network supports
    two types of shortest path queries:
      - By distance: finds the physically shortest route.
      - By time: uses speed profiles to estimate travel time at a given hour.

    This separation matters because the fastest route is often not the
    shortest — a highway detour may be longer in km but faster in minutes.
    """

    def __init__(self):
        self._intersections: dict[str, Intersection] = {}
        self._segments: dict[str, RoadSegment] = {}
        self._speed_profiles: dict[str, dict[int, SpeedProfile]] = {}  # segment_id -> {hour: profile}
        # Adjacency: intersection_id -> list of (neighbor_intersection_id, segment_id)
        self._adjacency: dict[str, list[tuple[str, str]]] = {}

    def add_intersection(self, intersection: Intersection) -> None:
        """Register an intersection (node) in the network."""
        self._intersections[intersection.id] = intersection
        if intersection.id not in self._adjacency:
            self._adjacency[intersection.id] = []

    def add_segment(
        self,
        segment: RoadSegment,
        from_intersection: str,
        to_intersection: str,
    ) -> None:
        """Add a road segment (directed edge) between two intersections.

        Both intersections must already exist in the network.
        """
        if from_intersection not in self._intersections:
            raise ValueError(f"Intersection '{from_intersection}' not found")
        if to_intersection not in self._intersections:
            raise ValueError(f"Intersection '{to_intersection}' not found")
        self._segments[segment.id] = segment
        self._adjacency[from_intersection].append((to_intersection, segment.id))

    def add_speed_profile(self, profile: SpeedProfile) -> None:
        """Register a speed profile for a segment at a specific hour."""
        if profile.segment_id not in self._speed_profiles:
            self._speed_profiles[profile.segment_id] = {}
        self._speed_profiles[profile.segment_id][profile.hour] = profile

    def get_segment(self, segment_id: str) -> RoadSegment:
        """Return the segment with the given id, or raise KeyError."""
        if segment_id not in self._segments:
            raise KeyError(f"Segment '{segment_id}' not found")
        return self._segments[segment_id]

    def get_congestion(self, segment_id: str, current_speed: float) -> CongestionLevel:
        """Determine congestion level by comparing current speed to the limit.

        Thresholds (ratio of current_speed / speed_limit):
          >= 0.8  -> FREE_FLOW
          >= 0.6  -> LIGHT
          >= 0.4  -> MODERATE
          >= 0.2  -> HEAVY
          <  0.2  -> GRIDLOCK
        """
        segment = self.get_segment(segment_id)
        if segment.speed_limit_kmh <= 0:
            return CongestionLevel.GRIDLOCK
        ratio = current_speed / segment.speed_limit_kmh
        if ratio >= 0.8:
            return CongestionLevel.FREE_FLOW
        elif ratio >= 0.6:
            return CongestionLevel.LIGHT
        elif ratio >= 0.4:
            return CongestionLevel.MODERATE
        elif ratio >= 0.2:
            return CongestionLevel.HEAVY
        else:
            return CongestionLevel.GRIDLOCK

    def _get_speed_for_segment(self, segment_id: str, hour: int) -> float:
        """Return the average speed for a segment at a given hour.

        Falls back to the segment's speed limit if no profile exists.
        """
        profiles = self._speed_profiles.get(segment_id, {})
        if hour in profiles:
            return profiles[hour].avg_speed
        return self._segments[segment_id].speed_limit_kmh

    def shortest_path_distance(self, from_id: str, to_id: str) -> float:
        """Find shortest path by total distance (km) using Dijkstra.

        Returns the total distance in km. Raises ValueError if no path exists.
        """
        if from_id not in self._intersections:
            raise ValueError(f"Intersection '{from_id}' not found")
        if to_id not in self._intersections:
            raise ValueError(f"Intersection '{to_id}' not found")

        dist = {from_id: 0.0}
        heap = [(0.0, from_id)]

        while heap:
            d, node = heapq.heappop(heap)
            if node == to_id:
                return d
            if d > dist.get(node, float("inf")):
                continue
            for nbr, seg_id in self._adjacency.get(node, []):
                seg = self._segments[seg_id]
                new_dist = d + seg.distance_km
                if new_dist < dist.get(nbr, float("inf")):
                    dist[nbr] = new_dist
                    heapq.heappush(heap, (new_dist, nbr))

        raise ValueError(f"No path from '{from_id}' to '{to_id}'")

    def shortest_path_time(self, from_id: str, to_id: str, hour: int) -> float:
        """Find shortest path by estimated travel time (minutes) using Dijkstra.

        Uses speed profiles for the given hour to estimate each segment's
        travel time. Returns total time in minutes.
        """
        if from_id not in self._intersections:
            raise ValueError(f"Intersection '{from_id}' not found")
        if to_id not in self._intersections:
            raise ValueError(f"Intersection '{to_id}' not found")

        dist = {from_id: 0.0}
        heap = [(0.0, from_id)]

        while heap:
            d, node = heapq.heappop(heap)
            if node == to_id:
                return d
            if d > dist.get(node, float("inf")):
                continue
            for nbr, seg_id in self._adjacency.get(node, []):
                seg = self._segments[seg_id]
                speed = self._get_speed_for_segment(seg_id, hour)
                travel_time = seg.get_travel_time(speed)
                new_dist = d + travel_time
                if new_dist < dist.get(nbr, float("inf")):
                    dist[nbr] = new_dist
                    heapq.heappush(heap, (new_dist, nbr))

        raise ValueError(f"No path from '{from_id}' to '{to_id}'")
