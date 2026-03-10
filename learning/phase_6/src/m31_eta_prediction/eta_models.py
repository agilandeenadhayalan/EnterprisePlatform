"""
ETA Prediction Models — From simple averages to graph-based approaches.

WHY THIS MATTERS:
ETA prediction is a core feature of ride-hailing platforms. The accuracy
of the ETA directly impacts rider trust, driver earnings, and dispatch
efficiency. This module implements three progressively more sophisticated
ETA models:

  1. HistoricalAverageETA: the simplest baseline — just average past trips.
  2. SegmentBasedETA: sum travel times along individual road segments,
     accounting for time-of-day speed variation.
  3. GraphBasedETA: use graph message passing to incorporate neighborhood
     context, capturing how congestion on adjacent roads affects your route.

In production, companies like Uber use deep learning variants of approach
#3 (DeepETA), but the core idea — propagating spatial context through a
road graph — is the same.
"""

from abc import ABC, abstractmethod
from .graph_networks import Graph, GraphNode, GraphEdge, MessagePassing


class BaseETAModel(ABC):
    """Abstract base class for ETA prediction models.

    All models take an origin, destination, and feature dict, and return
    estimated travel time in minutes.
    """

    @abstractmethod
    def predict(self, origin: str, destination: str, features: dict = None) -> float:
        """Predict travel time in minutes from origin to destination.

        Args:
            origin: origin identifier (intersection or zone id)
            destination: destination identifier
            features: optional dict of route/time features

        Returns:
            Estimated travel time in minutes.
        """


class HistoricalAverageETA(BaseETAModel):
    """ETA prediction based on historical trip averages.

    The simplest possible model: store all observed trip times for each
    origin-destination pair and return their mean. Despite its simplicity,
    this is a surprisingly strong baseline that many ML models struggle
    to beat significantly.
    """

    def __init__(self):
        self._history: dict[tuple[str, str], list[float]] = {}

    def add_observation(self, origin: str, destination: str, travel_time: float) -> None:
        """Record an observed trip time for an origin-destination pair."""
        key = (origin, destination)
        if key not in self._history:
            self._history[key] = []
        self._history[key].append(travel_time)

    def predict(self, origin: str, destination: str, features: dict = None) -> float:
        """Return the mean historical travel time for the OD pair.

        Raises ValueError if no historical data exists for this pair.
        """
        key = (origin, destination)
        if key not in self._history or not self._history[key]:
            raise ValueError(f"No historical data for ({origin}, {destination})")
        times = self._history[key]
        return sum(times) / len(times)

    @property
    def pair_count(self) -> int:
        """Number of OD pairs with historical data."""
        return len(self._history)


class SegmentBasedETA(BaseETAModel):
    """ETA prediction by summing individual segment travel times.

    Given a route as a list of segment IDs, look up each segment's
    expected speed for the given hour and sum the individual travel times.
    This is more accurate than historical averages because it accounts
    for time-of-day variation on each road segment independently.
    """

    def __init__(self, road_network):
        self._network = road_network

    def predict(self, origin: str, destination: str, features: dict = None) -> float:
        """Sum segment travel times along the route.

        features must contain:
          - 'route': list of segment IDs
          - 'hour': current hour (0-23)

        Returns total travel time in minutes.
        """
        if not features or "route" not in features or "hour" not in features:
            raise ValueError("features must contain 'route' and 'hour'")

        route = features["route"]
        hour = features["hour"]
        total_time = 0.0

        for seg_id in route:
            segment = self._network.get_segment(seg_id)
            speed = self._network._get_speed_for_segment(seg_id, hour)
            total_time += segment.get_travel_time(speed)

        return total_time


class GraphBasedETA(BaseETAModel):
    """ETA prediction using graph message passing.

    This model builds a graph from the road network where intersections
    are nodes and segments are edges. It runs multiple iterations of
    message passing so each node can aggregate information from its
    neighborhood, then sums the transformed edge weights along the route.

    This captures how congestion on adjacent roads affects travel time
    on your route — a key insight that segment-based models miss.
    """

    def __init__(self, road_network, iterations: int = 2):
        self._network = road_network
        self._iterations = iterations
        self._mp = MessagePassing()

    def predict(self, origin: str, destination: str, features: dict = None) -> float:
        """Predict ETA using graph message passing.

        features must contain:
          - 'route': list of (from_intersection, to_intersection, segment_id) tuples
          - 'hour': current hour (0-23)

        The model:
          1. Builds a graph with speed-based node features.
          2. Runs message passing for self._iterations steps.
          3. For each segment in the route, computes travel time adjusted
             by the aggregated neighborhood context.
        """
        if not features or "route" not in features or "hour" not in features:
            raise ValueError("features must contain 'route' and 'hour'")

        route = features["route"]
        hour = features["hour"]

        # Build graph from intersections and segments involved in the route
        graph = Graph()
        intersection_ids = set()
        for from_int, to_int, seg_id in route:
            intersection_ids.add(from_int)
            intersection_ids.add(to_int)

        # Add nodes with speed features
        for int_id in intersection_ids:
            # Node feature: average speed of connected segments at this hour
            speeds = []
            for nbr, seg_id in self._network._adjacency.get(int_id, []):
                speed = self._network._get_speed_for_segment(seg_id, hour)
                speeds.append(speed)
            avg_speed = sum(speeds) / len(speeds) if speeds else 50.0
            graph.add_node(GraphNode(int_id, {"speed": avg_speed}))

        # Add edges with distance-based weights
        for from_int, to_int, seg_id in route:
            seg = self._network.get_segment(seg_id)
            graph.add_edge(GraphEdge(from_int, to_int, weight=seg.distance_km))

        # Run message passing iterations
        node_features = {n.id: dict(n.features) for n in graph.nodes}
        for _ in range(self._iterations):
            aggregated = self._mp.propagate(graph)
            for node_id in node_features:
                if aggregated.get(node_id):
                    # Blend original and aggregated features
                    for feat, val in aggregated[node_id].items():
                        orig = node_features[node_id].get(feat, val)
                        node_features[node_id][feat] = 0.5 * orig + 0.5 * val
            # Update graph node features for next iteration
            for node_id, feats in node_features.items():
                graph.get_node(node_id).features = feats

        # Compute ETA: sum travel times using updated speed features
        total_time = 0.0
        for from_int, to_int, seg_id in route:
            seg = self._network.get_segment(seg_id)
            # Use the blended speed from message passing
            from_speed = node_features.get(from_int, {}).get("speed", 50.0)
            to_speed = node_features.get(to_int, {}).get("speed", 50.0)
            effective_speed = (from_speed + to_speed) / 2.0
            if effective_speed <= 0:
                effective_speed = 1.0
            total_time += seg.get_travel_time(effective_speed)

        return total_time
