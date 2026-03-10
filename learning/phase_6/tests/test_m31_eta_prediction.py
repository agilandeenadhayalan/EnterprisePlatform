"""
Tests for M31: ETA Prediction — Graph networks, road modeling, and
arrival time estimation.
"""

import math
import pytest

from m31_eta_prediction.graph_networks import (
    GraphNode,
    GraphEdge,
    Graph,
    MessagePassing,
    GraphConvolution,
)
from m31_eta_prediction.road_network import (
    CongestionLevel,
    RoadSegment,
    SpeedProfile,
    Intersection,
    RoadNetwork,
)
from m31_eta_prediction.eta_models import (
    HistoricalAverageETA,
    SegmentBasedETA,
    GraphBasedETA,
)
from m31_eta_prediction.route_features import RouteFeatureExtractor


# ── GraphNode ──


class TestGraphNode:
    def test_create_node(self):
        """GraphNode stores id and features."""
        n = GraphNode("A", {"speed": 60})
        assert n.id == "A"
        assert n.features == {"speed": 60}

    def test_default_features(self):
        """GraphNode defaults to empty features dict."""
        n = GraphNode("B")
        assert n.features == {}

    def test_repr(self):
        """GraphNode has a readable repr."""
        n = GraphNode("C", {"x": 1})
        assert "C" in repr(n)


# ── GraphEdge ──


class TestGraphEdge:
    def test_create_edge(self):
        """GraphEdge stores source, target, weight, and features."""
        e = GraphEdge("A", "B", 2.5, {"type": "highway"})
        assert e.source_id == "A"
        assert e.target_id == "B"
        assert e.weight == 2.5
        assert e.features == {"type": "highway"}

    def test_default_weight(self):
        """GraphEdge defaults to weight 1.0."""
        e = GraphEdge("A", "B")
        assert e.weight == 1.0

    def test_default_features(self):
        """GraphEdge defaults to empty features dict."""
        e = GraphEdge("A", "B", 1.0)
        assert e.features == {}


# ── Graph ──


class TestGraph:
    def test_add_node(self):
        """Graph can add and retrieve nodes."""
        g = Graph()
        g.add_node(GraphNode("A", {"speed": 50}))
        assert g.node_count == 1
        assert g.get_node("A").features["speed"] == 50

    def test_add_multiple_nodes(self):
        """Graph tracks multiple nodes."""
        g = Graph()
        g.add_node(GraphNode("A"))
        g.add_node(GraphNode("B"))
        g.add_node(GraphNode("C"))
        assert g.node_count == 3

    def test_get_node_not_found(self):
        """Getting a non-existent node raises KeyError."""
        g = Graph()
        with pytest.raises(KeyError):
            g.get_node("X")

    def test_add_edge(self):
        """Graph can add directed edges between existing nodes."""
        g = Graph()
        g.add_node(GraphNode("A"))
        g.add_node(GraphNode("B"))
        g.add_edge(GraphEdge("A", "B", 1.5))
        assert g.edge_count == 1

    def test_add_edge_missing_source(self):
        """Adding edge with missing source raises ValueError."""
        g = Graph()
        g.add_node(GraphNode("B"))
        with pytest.raises(ValueError, match="Source"):
            g.add_edge(GraphEdge("A", "B"))

    def test_add_edge_missing_target(self):
        """Adding edge with missing target raises ValueError."""
        g = Graph()
        g.add_node(GraphNode("A"))
        with pytest.raises(ValueError, match="Target"):
            g.add_edge(GraphEdge("A", "B"))

    def test_get_neighbors(self):
        """get_neighbors returns ids reachable via outgoing edges."""
        g = Graph()
        g.add_node(GraphNode("A"))
        g.add_node(GraphNode("B"))
        g.add_node(GraphNode("C"))
        g.add_edge(GraphEdge("A", "B"))
        g.add_edge(GraphEdge("A", "C"))
        neighbors = g.get_neighbors("A")
        assert set(neighbors) == {"B", "C"}

    def test_get_neighbors_empty(self):
        """Node with no outgoing edges has empty neighbors."""
        g = Graph()
        g.add_node(GraphNode("A"))
        assert g.get_neighbors("A") == []

    def test_get_neighbors_not_found(self):
        """Getting neighbors of non-existent node raises KeyError."""
        g = Graph()
        with pytest.raises(KeyError):
            g.get_neighbors("X")

    def test_get_edge(self):
        """get_edge returns the edge between two nodes."""
        g = Graph()
        g.add_node(GraphNode("A"))
        g.add_node(GraphNode("B"))
        g.add_edge(GraphEdge("A", "B", 3.0))
        e = g.get_edge("A", "B")
        assert e.weight == 3.0

    def test_get_edge_not_found(self):
        """Getting a non-existent edge raises KeyError."""
        g = Graph()
        g.add_node(GraphNode("A"))
        g.add_node(GraphNode("B"))
        with pytest.raises(KeyError):
            g.get_edge("A", "B")

    def test_directed_edges(self):
        """Edges are directed: A->B does not imply B->A."""
        g = Graph()
        g.add_node(GraphNode("A"))
        g.add_node(GraphNode("B"))
        g.add_edge(GraphEdge("A", "B"))
        assert "B" in g.get_neighbors("A")
        assert "A" not in g.get_neighbors("B")

    def test_nodes_property(self):
        """Graph.nodes returns all nodes."""
        g = Graph()
        g.add_node(GraphNode("A"))
        g.add_node(GraphNode("B"))
        assert len(g.nodes) == 2


# ── MessagePassing ──


class TestMessagePassing:
    def test_propagate_single_neighbor(self):
        """Message passing with one neighbor returns neighbor features."""
        g = Graph()
        g.add_node(GraphNode("A", {"speed": 0}))
        g.add_node(GraphNode("B", {"speed": 60}))
        g.add_edge(GraphEdge("A", "B", 1.0))
        mp = MessagePassing()
        result = mp.propagate(g)
        assert result["A"]["speed"] == pytest.approx(60.0)

    def test_propagate_weighted_mean(self):
        """Message passing computes weighted mean of neighbor features."""
        g = Graph()
        g.add_node(GraphNode("A", {"speed": 0}))
        g.add_node(GraphNode("B", {"speed": 60}))
        g.add_node(GraphNode("C", {"speed": 30}))
        g.add_edge(GraphEdge("A", "B", 0.5))
        g.add_edge(GraphEdge("A", "C", 1.0))
        mp = MessagePassing()
        result = mp.propagate(g)
        # (0.5*60 + 1.0*30) / (0.5 + 1.0) = 60/1.5 = 40
        assert result["A"]["speed"] == pytest.approx(40.0)

    def test_propagate_no_neighbors(self):
        """Node with no neighbors gets empty aggregation."""
        g = Graph()
        g.add_node(GraphNode("A", {"speed": 50}))
        mp = MessagePassing()
        result = mp.propagate(g)
        assert result["A"] == {}

    def test_propagate_multiple_features(self):
        """Message passing handles multiple feature dimensions."""
        g = Graph()
        g.add_node(GraphNode("A", {}))
        g.add_node(GraphNode("B", {"speed": 60, "capacity": 100}))
        g.add_edge(GraphEdge("A", "B", 1.0))
        mp = MessagePassing()
        result = mp.propagate(g)
        assert result["A"]["speed"] == pytest.approx(60.0)
        assert result["A"]["capacity"] == pytest.approx(100.0)


# ── GraphConvolution ──


class TestGraphConvolution:
    def test_forward_basic(self):
        """Graph convolution applies weight matrix to aggregated features."""
        g = Graph()
        g.add_node(GraphNode("A", {}))
        g.add_node(GraphNode("B", {"speed": 60}))
        g.add_edge(GraphEdge("A", "B", 1.0))
        gc = GraphConvolution()
        wm = {"speed": {"eta": 0.5}}
        result = gc.forward(g, wm)
        # Aggregated speed for A = 60, then eta = 60 * 0.5 = 30
        assert result["A"]["eta"] == pytest.approx(30.0)

    def test_forward_no_neighbors(self):
        """Node with no neighbors produces no output features."""
        g = Graph()
        g.add_node(GraphNode("A", {"speed": 50}))
        gc = GraphConvolution()
        wm = {"speed": {"eta": 1.0}}
        result = gc.forward(g, wm)
        assert result["A"] == {}

    def test_forward_multiple_outputs(self):
        """Weight matrix can map one input feature to multiple outputs."""
        g = Graph()
        g.add_node(GraphNode("A", {}))
        g.add_node(GraphNode("B", {"speed": 100}))
        g.add_edge(GraphEdge("A", "B", 1.0))
        gc = GraphConvolution()
        wm = {"speed": {"eta": 0.5, "risk": 0.1}}
        result = gc.forward(g, wm)
        assert result["A"]["eta"] == pytest.approx(50.0)
        assert result["A"]["risk"] == pytest.approx(10.0)


# ── RoadSegment ──


class TestRoadSegment:
    def test_travel_time(self):
        """Travel time = distance / speed * 60 minutes."""
        seg = RoadSegment("s1", "Main St", distance_km=10.0, lanes=2, speed_limit_kmh=60)
        assert seg.get_travel_time(60) == pytest.approx(10.0)

    def test_travel_time_slow(self):
        """Slower speed means longer travel time."""
        seg = RoadSegment("s1", "Main St", distance_km=10.0, lanes=2, speed_limit_kmh=60)
        assert seg.get_travel_time(30) == pytest.approx(20.0)

    def test_travel_time_zero_speed(self):
        """Zero speed raises ValueError."""
        seg = RoadSegment("s1", "Main St", distance_km=10.0, lanes=2, speed_limit_kmh=60)
        with pytest.raises(ValueError, match="positive"):
            seg.get_travel_time(0)

    def test_road_type(self):
        """RoadSegment stores road type."""
        seg = RoadSegment("s1", "Highway 1", 5.0, 4, 100, "highway")
        assert seg.road_type == "highway"


# ── CongestionLevel ──


class TestCongestionLevel:
    def test_free_flow(self):
        """Speed >= 80% of limit is FREE_FLOW."""
        net = RoadNetwork()
        net.add_intersection(Intersection("A", "Start"))
        net.add_intersection(Intersection("B", "End"))
        seg = RoadSegment("s1", "Main", 5.0, 2, 100)
        net.add_segment(seg, "A", "B")
        assert net.get_congestion("s1", 85) == CongestionLevel.FREE_FLOW

    def test_light(self):
        """Speed 60-79% of limit is LIGHT."""
        net = RoadNetwork()
        net.add_intersection(Intersection("A", "Start"))
        net.add_intersection(Intersection("B", "End"))
        seg = RoadSegment("s1", "Main", 5.0, 2, 100)
        net.add_segment(seg, "A", "B")
        assert net.get_congestion("s1", 70) == CongestionLevel.LIGHT

    def test_moderate(self):
        """Speed 40-59% of limit is MODERATE."""
        net = RoadNetwork()
        net.add_intersection(Intersection("A", "Start"))
        net.add_intersection(Intersection("B", "End"))
        seg = RoadSegment("s1", "Main", 5.0, 2, 100)
        net.add_segment(seg, "A", "B")
        assert net.get_congestion("s1", 50) == CongestionLevel.MODERATE

    def test_heavy(self):
        """Speed 20-39% of limit is HEAVY."""
        net = RoadNetwork()
        net.add_intersection(Intersection("A", "Start"))
        net.add_intersection(Intersection("B", "End"))
        seg = RoadSegment("s1", "Main", 5.0, 2, 100)
        net.add_segment(seg, "A", "B")
        assert net.get_congestion("s1", 25) == CongestionLevel.HEAVY

    def test_gridlock(self):
        """Speed < 20% of limit is GRIDLOCK."""
        net = RoadNetwork()
        net.add_intersection(Intersection("A", "Start"))
        net.add_intersection(Intersection("B", "End"))
        seg = RoadSegment("s1", "Main", 5.0, 2, 100)
        net.add_segment(seg, "A", "B")
        assert net.get_congestion("s1", 10) == CongestionLevel.GRIDLOCK


# ── SpeedProfile ──


class TestSpeedProfile:
    def test_create_profile(self):
        """SpeedProfile stores segment_id, hour, avg_speed, stddev."""
        sp = SpeedProfile("s1", 8, 30.0, 5.0)
        assert sp.segment_id == "s1"
        assert sp.hour == 8
        assert sp.avg_speed == 30.0
        assert sp.stddev == 5.0

    def test_invalid_hour(self):
        """Hour outside 0-23 raises ValueError."""
        with pytest.raises(ValueError, match="0-23"):
            SpeedProfile("s1", 25, 50.0)


# ── RoadNetwork Dijkstra ──


class TestRoadNetworkDijkstra:
    def _build_network(self):
        """Build a small test road network: A --(5km)--> B --(3km)--> C."""
        net = RoadNetwork()
        net.add_intersection(Intersection("A", "Start"))
        net.add_intersection(Intersection("B", "Middle"))
        net.add_intersection(Intersection("C", "End"))
        net.add_segment(RoadSegment("s1", "Seg1", 5.0, 2, 60), "A", "B")
        net.add_segment(RoadSegment("s2", "Seg2", 3.0, 2, 60), "B", "C")
        return net

    def test_shortest_path_distance_direct(self):
        """Shortest distance A->B is 5 km."""
        net = self._build_network()
        assert net.shortest_path_distance("A", "B") == pytest.approx(5.0)

    def test_shortest_path_distance_multi_hop(self):
        """Shortest distance A->C via B is 8 km."""
        net = self._build_network()
        assert net.shortest_path_distance("A", "C") == pytest.approx(8.0)

    def test_shortest_path_distance_no_path(self):
        """No path raises ValueError."""
        net = self._build_network()
        with pytest.raises(ValueError, match="No path"):
            net.shortest_path_distance("C", "A")

    def test_shortest_path_time(self):
        """Shortest time uses speed profiles for the given hour."""
        net = self._build_network()
        net.add_speed_profile(SpeedProfile("s1", 8, 30.0))  # rush hour
        net.add_speed_profile(SpeedProfile("s2", 8, 60.0))
        # s1: 5km / 30kmh * 60 = 10 min, s2: 3km / 60kmh * 60 = 3 min
        assert net.shortest_path_time("A", "C", 8) == pytest.approx(13.0)

    def test_shortest_path_time_fallback_to_limit(self):
        """Without speed profile, falls back to speed limit."""
        net = self._build_network()
        # No profiles, speed limit is 60 for both
        # s1: 5/60*60=5 min, s2: 3/60*60=3 min
        assert net.shortest_path_time("A", "C", 12) == pytest.approx(8.0)

    def test_add_segment_invalid_intersection(self):
        """Adding segment with non-existent intersection raises ValueError."""
        net = RoadNetwork()
        net.add_intersection(Intersection("A", "Start"))
        with pytest.raises(ValueError, match="not found"):
            net.add_segment(RoadSegment("s1", "Seg1", 5.0, 2, 60), "A", "X")


# ── HistoricalAverageETA ──


class TestHistoricalAverageETA:
    def test_predict_single_observation(self):
        """With one observation, returns that value."""
        model = HistoricalAverageETA()
        model.add_observation("A", "B", 15.0)
        assert model.predict("A", "B") == pytest.approx(15.0)

    def test_predict_average(self):
        """Returns mean of all observations for the OD pair."""
        model = HistoricalAverageETA()
        model.add_observation("A", "B", 10.0)
        model.add_observation("A", "B", 20.0)
        assert model.predict("A", "B") == pytest.approx(15.0)

    def test_predict_no_data(self):
        """Predicting without data raises ValueError."""
        model = HistoricalAverageETA()
        with pytest.raises(ValueError, match="No historical"):
            model.predict("A", "B")

    def test_pair_count(self):
        """pair_count tracks distinct OD pairs."""
        model = HistoricalAverageETA()
        model.add_observation("A", "B", 10.0)
        model.add_observation("A", "C", 20.0)
        assert model.pair_count == 2


# ── SegmentBasedETA ──


class TestSegmentBasedETA:
    def test_predict_sums_segments(self):
        """SegmentBasedETA sums individual segment travel times."""
        net = RoadNetwork()
        net.add_intersection(Intersection("A", "Start"))
        net.add_intersection(Intersection("B", "Mid"))
        net.add_intersection(Intersection("C", "End"))
        net.add_segment(RoadSegment("s1", "Seg1", 5.0, 2, 60), "A", "B")
        net.add_segment(RoadSegment("s2", "Seg2", 3.0, 2, 60), "B", "C")
        net.add_speed_profile(SpeedProfile("s1", 10, 60.0))
        net.add_speed_profile(SpeedProfile("s2", 10, 30.0))

        model = SegmentBasedETA(net)
        # s1: 5/60*60 = 5 min, s2: 3/30*60 = 6 min
        eta = model.predict("A", "C", {"route": ["s1", "s2"], "hour": 10})
        assert eta == pytest.approx(11.0)

    def test_predict_missing_features(self):
        """Missing route or hour raises ValueError."""
        net = RoadNetwork()
        model = SegmentBasedETA(net)
        with pytest.raises(ValueError, match="route"):
            model.predict("A", "B", {})


# ── GraphBasedETA ──


class TestGraphBasedETA:
    def test_predict_returns_positive(self):
        """GraphBasedETA returns a positive ETA."""
        net = RoadNetwork()
        net.add_intersection(Intersection("A", "Start"))
        net.add_intersection(Intersection("B", "End"))
        net.add_segment(RoadSegment("s1", "Seg1", 10.0, 2, 60), "A", "B")
        net.add_speed_profile(SpeedProfile("s1", 8, 40.0))

        model = GraphBasedETA(net, iterations=2)
        route = [("A", "B", "s1")]
        eta = model.predict("A", "B", {"route": route, "hour": 8})
        assert eta > 0

    def test_predict_missing_features(self):
        """Missing features raises ValueError."""
        net = RoadNetwork()
        model = GraphBasedETA(net)
        with pytest.raises(ValueError, match="route"):
            model.predict("A", "B")


# ── RouteFeatureExtractor ──


class TestRouteFeatureExtractor:
    def _build_network(self):
        net = RoadNetwork()
        net.add_intersection(Intersection("A", "Start"))
        net.add_intersection(Intersection("B", "Mid"))
        net.add_intersection(Intersection("C", "End"))
        net.add_segment(RoadSegment("s1", "Seg1", 5.0, 2, 100, "highway"), "A", "B")
        net.add_segment(RoadSegment("s2", "Seg2", 3.0, 2, 60, "urban"), "B", "C")
        net.add_speed_profile(SpeedProfile("s1", 8, 80.0))
        net.add_speed_profile(SpeedProfile("s2", 8, 25.0))
        return net

    def test_total_distance(self):
        """Total distance sums segment distances."""
        net = self._build_network()
        ext = RouteFeatureExtractor(net)
        assert ext.total_distance(["s1", "s2"]) == pytest.approx(8.0)

    def test_num_turns_different_types(self):
        """Turn detected when consecutive segments differ in road type."""
        net = self._build_network()
        ext = RouteFeatureExtractor(net)
        assert ext.num_turns(["s1", "s2"]) == 1

    def test_num_turns_same_type(self):
        """No turns when segments have the same road type."""
        net = RoadNetwork()
        net.add_intersection(Intersection("A", "A"))
        net.add_intersection(Intersection("B", "B"))
        net.add_intersection(Intersection("C", "C"))
        net.add_segment(RoadSegment("s1", "Seg1", 5.0, 2, 60, "urban"), "A", "B")
        net.add_segment(RoadSegment("s2", "Seg2", 3.0, 2, 60, "urban"), "B", "C")
        ext = RouteFeatureExtractor(net)
        assert ext.num_turns(["s1", "s2"]) == 0

    def test_road_type_distribution(self):
        """Road type distribution as fractions."""
        net = self._build_network()
        ext = RouteFeatureExtractor(net)
        dist = ext.road_type_distribution(["s1", "s2"])
        assert dist["highway"] == pytest.approx(0.5)
        assert dist["urban"] == pytest.approx(0.5)

    def test_time_of_day_features_midnight(self):
        """Hour 0 encodes to sin=0, cos=1."""
        net = self._build_network()
        ext = RouteFeatureExtractor(net)
        feats = ext.time_of_day_features(0)
        assert feats["hour_sin"] == pytest.approx(0.0)
        assert feats["hour_cos"] == pytest.approx(1.0)

    def test_time_of_day_features_6am(self):
        """Hour 6 encodes to sin=1, cos=0 (quarter cycle)."""
        net = self._build_network()
        ext = RouteFeatureExtractor(net)
        feats = ext.time_of_day_features(6)
        assert feats["hour_sin"] == pytest.approx(1.0)
        assert feats["hour_cos"] == pytest.approx(0.0, abs=1e-10)

    def test_congestion_ratio(self):
        """Congestion ratio counts segments with moderate+ congestion."""
        net = self._build_network()
        ext = RouteFeatureExtractor(net)
        # s1 at hour 8: speed 80, limit 100 -> ratio 0.8 = FREE_FLOW
        # s2 at hour 8: speed 25, limit 60 -> ratio 0.42 = MODERATE
        ratio = ext.congestion_ratio(["s1", "s2"], 8)
        assert ratio == pytest.approx(0.5)

    def test_extract_all_keys(self):
        """extract_all returns all expected feature keys."""
        net = self._build_network()
        ext = RouteFeatureExtractor(net)
        feats = ext.extract_all(["s1", "s2"], 8)
        assert "total_distance" in feats
        assert "num_turns" in feats
        assert "congestion_ratio" in feats
        assert "hour_sin" in feats
        assert "hour_cos" in feats
