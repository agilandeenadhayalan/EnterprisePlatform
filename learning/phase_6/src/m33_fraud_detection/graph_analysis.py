"""
Transaction Graph Analysis — Network-based fraud detection.

WHY THIS MATTERS:
Fraudsters operate in networks. A single fraudulent transaction might
look normal, but when you see a user sending money to 50 accounts in
one hour, or money going A -> B -> A (round-tripping), the pattern
becomes obvious. Graph analysis reveals these structural anomalies.

Key concepts:
  - Fan-out: a user sending to many recipients in a short time.
  - Rapid transactions: many transactions within a narrow time window.
  - Round-trip detection: money flowing in a cycle (laundering indicator).
  - PageRank: identifies important nodes — fraudulent accounts often have
    unusual PageRank scores (very high or very low).
"""


class TransactionNode:
    """A node in the transaction graph (user or merchant).

    node_type distinguishes users, merchants, ATMs, etc. Attributes
    hold metadata like account age, location, and verification status.
    """

    def __init__(self, id: str, node_type: str = "user", attributes: dict = None):
        self.id = id
        self.node_type = node_type
        self.attributes = attributes or {}


class TransactionEdge:
    """A directed transaction edge between two nodes.

    Represents money flowing from source to target. Timestamp is a
    string (ISO format) for simplicity; production systems use proper
    datetime objects.
    """

    def __init__(self, source_id: str, target_id: str, amount: float, timestamp: str = ""):
        self.source_id = source_id
        self.target_id = target_id
        self.amount = amount
        self.timestamp = timestamp


class TransactionGraph:
    """A directed graph of transactions between nodes.

    Supports node/edge addition and basic graph queries like fan-out
    (number of outgoing edges) and fan-in (number of incoming edges).
    """

    def __init__(self):
        self._nodes: dict[str, TransactionNode] = {}
        self._outgoing: dict[str, list[TransactionEdge]] = {}  # node_id -> outgoing edges
        self._incoming: dict[str, list[TransactionEdge]] = {}  # node_id -> incoming edges

    def add_node(self, node: TransactionNode) -> None:
        """Add a node to the graph."""
        self._nodes[node.id] = node
        if node.id not in self._outgoing:
            self._outgoing[node.id] = []
        if node.id not in self._incoming:
            self._incoming[node.id] = []

    def add_edge(self, edge: TransactionEdge) -> None:
        """Add a transaction edge. Source and target must exist."""
        if edge.source_id not in self._nodes:
            raise ValueError(f"Source node '{edge.source_id}' not found")
        if edge.target_id not in self._nodes:
            raise ValueError(f"Target node '{edge.target_id}' not found")
        self._outgoing[edge.source_id].append(edge)
        self._incoming[edge.target_id].append(edge)

    def get_node(self, node_id: str) -> TransactionNode:
        """Return the node with the given id, or raise KeyError."""
        if node_id not in self._nodes:
            raise KeyError(f"Node '{node_id}' not found")
        return self._nodes[node_id]

    def get_edges(self, node_id: str) -> list[TransactionEdge]:
        """Return all edges (outgoing + incoming) for a node."""
        out = self._outgoing.get(node_id, [])
        inc = self._incoming.get(node_id, [])
        return out + inc

    def get_outgoing(self, node_id: str) -> list[TransactionEdge]:
        """Return outgoing edges for a node."""
        return list(self._outgoing.get(node_id, []))

    def get_incoming(self, node_id: str) -> list[TransactionEdge]:
        """Return incoming edges for a node."""
        return list(self._incoming.get(node_id, []))

    def fan_out(self, node_id: str) -> int:
        """Count of distinct targets this node sends to."""
        edges = self._outgoing.get(node_id, [])
        return len(set(e.target_id for e in edges))

    def fan_in(self, node_id: str) -> int:
        """Count of distinct sources sending to this node."""
        edges = self._incoming.get(node_id, [])
        return len(set(e.source_id for e in edges))

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def all_nodes(self) -> list[TransactionNode]:
        return list(self._nodes.values())

    @property
    def all_edges(self) -> list[TransactionEdge]:
        edges = []
        for edge_list in self._outgoing.values():
            edges.extend(edge_list)
        return edges


class SuspiciousPatternFinder:
    """Detect suspicious patterns in a transaction graph.

    These patterns are common indicators of fraudulent activity:
      - Fan-out: one account sending to many recipients (money mule).
      - Rapid transactions: many transactions in a short window (bot).
      - Round-trip: A -> B -> A money flow (laundering).
    """

    def detect_fan_out(self, graph: TransactionGraph, threshold: int = 5) -> list[str]:
        """Find nodes with fan-out exceeding the threshold.

        High fan-out is suspicious because legitimate users rarely send
        money to many different recipients in a short period.
        """
        suspicious = []
        for node in graph.all_nodes:
            if graph.fan_out(node.id) > threshold:
                suspicious.append(node.id)
        return suspicious

    def detect_rapid_transactions(
        self, graph: TransactionGraph, node_id: str, window_seconds: int = 60
    ) -> list[TransactionEdge]:
        """Find transactions from a node within a time window.

        Rapid-fire transactions suggest automated/bot activity. We parse
        timestamps and find clusters of transactions within window_seconds.
        """
        edges = graph.get_outgoing(node_id)
        if not edges:
            return []

        # Parse timestamps and sort
        timed_edges = []
        for e in edges:
            try:
                ts = self._parse_timestamp(e.timestamp)
                timed_edges.append((ts, e))
            except (ValueError, TypeError):
                continue

        timed_edges.sort(key=lambda x: x[0])

        # Find clusters within the window
        rapid = []
        for i, (ts_i, edge_i) in enumerate(timed_edges):
            cluster = [edge_i]
            for j in range(i + 1, len(timed_edges)):
                ts_j, edge_j = timed_edges[j]
                if ts_j - ts_i <= window_seconds:
                    cluster.append(edge_j)
                else:
                    break
            if len(cluster) >= 2:
                for e in cluster:
                    if e not in rapid:
                        rapid.append(e)

        return rapid

    @staticmethod
    def _parse_timestamp(ts_str: str) -> float:
        """Parse a simple timestamp string to seconds since epoch.

        Supports format: 'YYYY-MM-DD HH:MM:SS' or just seconds as string.
        For simplicity, we compute a relative second count.
        """
        if not ts_str:
            raise ValueError("Empty timestamp")
        parts = ts_str.strip().split()
        if len(parts) == 2:
            date_parts = parts[0].split("-")
            time_parts = parts[1].split(":")
            # Simplified: compute seconds from a reference
            days = int(date_parts[0]) * 365 + int(date_parts[1]) * 30 + int(date_parts[2])
            secs = int(time_parts[0]) * 3600 + int(time_parts[1]) * 60 + int(time_parts[2])
            return days * 86400 + secs
        # Try as a raw number
        return float(ts_str)

    def detect_round_trip(self, graph: TransactionGraph) -> list[tuple[str, str]]:
        """Detect A -> B -> A patterns (round-trip money flows).

        Round-tripping is a common money laundering technique where money
        is sent to a destination and then returned, often through
        intermediaries. Here we detect direct A -> B -> A cycles.
        """
        round_trips = []
        seen = set()

        for edge in graph.all_edges:
            a, b = edge.source_id, edge.target_id
            if a == b:
                continue
            # Check if there's a reverse edge B -> A
            reverse_edges = graph.get_outgoing(b)
            for rev in reverse_edges:
                if rev.target_id == a:
                    pair = tuple(sorted([a, b]))
                    if pair not in seen:
                        seen.add(pair)
                        round_trips.append((a, b))
                    break

        return round_trips


def SimplePageRank(
    graph: TransactionGraph, damping: float = 0.85, iterations: int = 20
) -> dict[str, float]:
    """Compute PageRank scores for all nodes in the transaction graph.

    PageRank measures the importance of nodes based on the structure of
    incoming links. Originally designed for web pages, it's useful in
    fraud detection because fraudulent accounts often have unusual
    PageRank scores.

    The iterative formula:
      PR(v) = (1 - d) / N + d * sum(PR(u) / out_degree(u) for u in in_neighbors(v))

    Args:
        graph: the transaction graph.
        damping: damping factor (probability of following a link). Default 0.85.
        iterations: number of power iterations. Default 20.

    Returns:
        Dict mapping node_id to PageRank score.
    """
    nodes = graph.all_nodes
    n = len(nodes)
    if n == 0:
        return {}

    node_ids = [node.id for node in nodes]
    pr = {nid: 1.0 / n for nid in node_ids}

    for _ in range(iterations):
        new_pr = {}
        for nid in node_ids:
            # Sum contributions from incoming edges
            incoming = graph.get_incoming(nid)
            rank_sum = 0.0
            for edge in incoming:
                src = edge.source_id
                out_degree = len(graph.get_outgoing(src))
                if out_degree > 0:
                    rank_sum += pr[src] / out_degree
            new_pr[nid] = (1 - damping) / n + damping * rank_sum
        pr = new_pr

    return pr
