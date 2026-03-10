"""
Exercise 1: Dijkstra with Time-Varying Edge Weights
========================================
Implement shortest path finding on a graph where edge travel times
change by hour of day. This models real-world road networks where
rush hour congestion makes some roads much slower.

WHY THIS MATTERS:
Static shortest path algorithms assume fixed edge weights, but real
road networks have time-varying speeds. A route that's fastest at
3 AM might be terrible at 8 AM. Time-varying Dijkstra is used by
every navigation app (Google Maps, Waze, etc.) to provide accurate
ETAs that account for current and predicted traffic.

The key difference from standard Dijkstra: as you traverse edges,
the arrival time at each node changes, which affects the travel time
of subsequent edges. You must use the arrival time at each intermediate
node to look up the correct speed for the next edge.

YOUR TASK:
Implement shortest_path(graph, source, destination, departure_hour)
that returns (path, total_minutes).

The graph has edges with speed_by_hour dicts mapping hour -> speed_kmh.
Travel time for an edge = distance_km / speed_kmh * 60 minutes.

When you arrive at a node at a fractional hour, use the floor of the
hour to look up the speed (e.g., arrival at 8.5 hours -> use hour 8).
"""

import heapq
import math


class TimeVaryingEdge:
    """A road edge with speeds that vary by hour of day."""

    def __init__(self, target: str, distance_km: float, speed_by_hour: dict[int, float]):
        self.target = target
        self.distance_km = distance_km
        self.speed_by_hour = speed_by_hour  # hour (0-23) -> speed_kmh

    def get_travel_time(self, hour: int) -> float:
        """Return travel time in minutes at the given hour.

        Uses speed_by_hour to look up speed. If the hour is not in the
        dict, uses the default speed of 50 km/h.
        """
        speed = self.speed_by_hour.get(hour, 50.0)
        if speed <= 0:
            return float("inf")
        return (self.distance_km / speed) * 60.0


class TimeVaryingGraph:
    """A graph with time-varying edge weights."""

    def __init__(self):
        self.adjacency: dict[str, list[TimeVaryingEdge]] = {}

    def add_node(self, node_id: str) -> None:
        if node_id not in self.adjacency:
            self.adjacency[node_id] = []

    def add_edge(self, source: str, edge: TimeVaryingEdge) -> None:
        if source not in self.adjacency:
            self.adjacency[source] = []
        self.adjacency[source].append(edge)


def shortest_path(
    graph: TimeVaryingGraph,
    source: str,
    destination: str,
    departure_hour: int,
) -> tuple[list[str], float]:
    """Find the shortest path considering time-varying edge speeds.

    As you traverse the graph, the current time advances. The speed on
    each edge depends on the hour you arrive at its source node. Use
    int(current_hour % 24) to look up the speed for each edge.

    Args:
        graph: the time-varying graph.
        source: starting node id.
        destination: ending node id.
        departure_hour: hour of departure (0-23).

    Returns:
        (path, total_minutes) where path is a list of node ids from
        source to destination, and total_minutes is the total travel time.

    Raises:
        ValueError: if no path exists.
    """
    # YOUR CODE HERE (~25 lines)
    # Hints:
    # 1. Use a priority queue (min-heap) of (total_minutes, node_id, path)
    # 2. Track the best known time to reach each node
    # 3. For each edge, compute current_hour = int((departure_hour + total_minutes/60) % 24)
    # 4. Use edge.get_travel_time(current_hour) to get the edge weight
    # 5. Don't forget to handle the case where no path exists
    raise NotImplementedError("Implement shortest_path")


# ── Verification ──


def _verify():
    """Run basic checks to verify your implementation."""
    g = TimeVaryingGraph()
    for node in ["A", "B", "C", "D", "E"]:
        g.add_node(node)

    # A -> B: 10 km, fast at night (100 kmh), slow at rush hour (20 kmh)
    g.add_edge("A", TimeVaryingEdge("B", 10.0, {3: 100, 8: 20, 12: 60}))
    # A -> C: 5 km, constant speed 50 kmh
    g.add_edge("A", TimeVaryingEdge("C", 5.0, {3: 50, 8: 50, 12: 50}))
    # B -> D: 5 km, fast always
    g.add_edge("B", TimeVaryingEdge("D", 5.0, {3: 100, 8: 100, 12: 100}))
    # C -> D: 15 km, slow at rush hour
    g.add_edge("C", TimeVaryingEdge("D", 15.0, {3: 100, 8: 25, 12: 60}))
    # D -> E: 2 km, constant
    g.add_edge("D", TimeVaryingEdge("E", 2.0, {3: 60, 8: 60, 12: 60}))

    # Test 1: At 3 AM (no traffic), A->B->D->E should be fastest
    path, minutes = shortest_path(g, "A", "E", 3)
    assert "A" in path and "E" in path, f"Path must include A and E, got {path}"
    assert minutes > 0, f"Travel time must be positive, got {minutes}"
    print(f"[PASS] Night route: {' -> '.join(path)} in {minutes:.1f} min")

    # Test 2: At rush hour (8 AM), route may differ
    path2, minutes2 = shortest_path(g, "A", "E", 8)
    assert "A" in path2 and "E" in path2
    print(f"[PASS] Rush hour route: {' -> '.join(path2)} in {minutes2:.1f} min")

    # Test 3: Rush hour should take longer than night
    assert minutes2 > minutes, (
        f"Rush hour ({minutes2:.1f}) should take longer than night ({minutes:.1f})"
    )
    print("[PASS] Rush hour takes longer than night")

    # Test 4: No path raises ValueError
    try:
        shortest_path(g, "E", "A", 8)
        assert False, "Should have raised ValueError for no path"
    except ValueError:
        print("[PASS] No path raises ValueError")

    print("\nAll checks passed!")


if __name__ == "__main__":
    _verify()
