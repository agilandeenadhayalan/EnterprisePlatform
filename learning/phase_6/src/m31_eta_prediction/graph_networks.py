"""
Pure-Python Graph Neural Network Primitives.

WHY THIS MATTERS:
Graph neural networks (GNNs) power ETA prediction at companies like Uber
(DeepETA) and Google Maps. Understanding message passing — the core GNN
operation — shows how spatial relationships in road networks can be learned
and exploited for better travel time predictions.

Key concepts:
  - Graph: adjacency list representation of nodes and directed edges.
  - MessagePassing: for each node, aggregate information from neighbors.
    This is how GNNs propagate spatial context through a network.
  - GraphConvolution: message passing + linear transformation, the building
    block of Graph Convolutional Networks (GCNs).
"""


class GraphNode:
    """A node in a graph with an associated feature dictionary.

    Features might include things like road capacity, historical speed,
    or intersection type — any numeric attribute the GNN can learn from.
    """

    def __init__(self, id: str, features: dict = None):
        self.id = id
        self.features = features or {}

    def __repr__(self):
        return f"GraphNode(id={self.id!r}, features={self.features})"


class GraphEdge:
    """A weighted directed edge between two nodes.

    Weight typically represents distance or travel time. Features can
    include road type, number of lanes, or current congestion level.
    """

    def __init__(self, source_id: str, target_id: str, weight: float = 1.0, features: dict = None):
        self.source_id = source_id
        self.target_id = target_id
        self.weight = weight
        self.features = features or {}

    def __repr__(self):
        return (
            f"GraphEdge(source={self.source_id!r}, target={self.target_id!r}, "
            f"weight={self.weight})"
        )


class Graph:
    """Adjacency list graph supporting directed, weighted edges.

    The graph stores nodes and edges separately, with an adjacency list
    mapping each node to its outgoing edges. This representation supports
    efficient neighbor lookups needed for message passing.
    """

    def __init__(self):
        self._nodes: dict[str, GraphNode] = {}
        self._edges: dict[tuple[str, str], GraphEdge] = {}
        self._adjacency: dict[str, list[str]] = {}  # node_id -> list of neighbor ids

    def add_node(self, node: GraphNode) -> None:
        """Add a node to the graph."""
        self._nodes[node.id] = node
        if node.id not in self._adjacency:
            self._adjacency[node.id] = []

    def add_edge(self, edge: GraphEdge) -> None:
        """Add a directed edge. Both source and target must already exist."""
        if edge.source_id not in self._nodes:
            raise ValueError(f"Source node '{edge.source_id}' not in graph")
        if edge.target_id not in self._nodes:
            raise ValueError(f"Target node '{edge.target_id}' not in graph")
        self._edges[(edge.source_id, edge.target_id)] = edge
        if edge.target_id not in self._adjacency[edge.source_id]:
            self._adjacency[edge.source_id].append(edge.target_id)

    def get_node(self, node_id: str) -> GraphNode:
        """Return the node with the given id, or raise KeyError."""
        if node_id not in self._nodes:
            raise KeyError(f"Node '{node_id}' not found")
        return self._nodes[node_id]

    def get_neighbors(self, node_id: str) -> list[str]:
        """Return ids of nodes reachable via outgoing edges from node_id."""
        if node_id not in self._nodes:
            raise KeyError(f"Node '{node_id}' not found")
        return list(self._adjacency.get(node_id, []))

    def get_edge(self, source_id: str, target_id: str) -> GraphEdge:
        """Return the edge from source to target, or raise KeyError."""
        key = (source_id, target_id)
        if key not in self._edges:
            raise KeyError(f"Edge ({source_id} -> {target_id}) not found")
        return self._edges[key]

    @property
    def node_count(self) -> int:
        """Number of nodes in the graph."""
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        """Number of edges in the graph."""
        return len(self._edges)

    @property
    def nodes(self) -> list[GraphNode]:
        """Return all nodes."""
        return list(self._nodes.values())

    @property
    def edges(self) -> list[GraphEdge]:
        """Return all edges."""
        return list(self._edges.values())


class MessagePassing:
    """Single-step message passing on a graph.

    For each node, aggregate neighbor features by computing the weighted
    mean of each feature across all neighbors. Edge weights act as
    importance multipliers. This is the core GNN operation — it lets
    each node incorporate information from its local neighborhood.

    Example: if node A has neighbors B (weight 0.5, speed=60) and
    C (weight 1.0, speed=30), the aggregated speed for A is:
    (0.5*60 + 1.0*30) / (0.5 + 1.0) = 40.0
    """

    def propagate(self, graph: Graph) -> dict[str, dict]:
        """Run one step of message passing.

        Returns a dict mapping each node_id to its aggregated feature dict.
        Nodes with no neighbors get an empty feature dict.
        """
        result = {}
        for node in graph.nodes:
            neighbors = graph.get_neighbors(node.id)
            if not neighbors:
                result[node.id] = {}
                continue

            # Collect weighted features from neighbors
            total_weight = 0.0
            feature_sums: dict[str, float] = {}
            for nbr_id in neighbors:
                edge = graph.get_edge(node.id, nbr_id)
                nbr_node = graph.get_node(nbr_id)
                w = edge.weight
                total_weight += w
                for feat_name, feat_val in nbr_node.features.items():
                    feature_sums[feat_name] = feature_sums.get(feat_name, 0.0) + w * feat_val

            # Weighted mean
            if total_weight > 0:
                aggregated = {k: v / total_weight for k, v in feature_sums.items()}
            else:
                aggregated = {}
            result[node.id] = aggregated
        return result


class GraphConvolution:
    """Graph convolution = message passing + linear transformation.

    After aggregating neighbor features, multiply by a weight matrix
    to produce output features. This is analogous to a dense layer in
    a neural network, but applied per-node on graph-structured data.

    The weight_matrix is a dict mapping input_feature_name to a dict
    mapping output_feature_name to weight. For example:
        {"speed": {"eta_component": 0.5}, "distance": {"eta_component": 0.3}}
    transforms speed and distance into a single eta_component.
    """

    def __init__(self):
        self._mp = MessagePassing()

    def forward(self, graph: Graph, weight_matrix: dict) -> dict[str, dict]:
        """Apply graph convolution.

        1. Run message passing to aggregate neighbor features.
        2. For each node, multiply aggregated features by weight_matrix.

        Returns dict mapping node_id to output feature dict.
        """
        aggregated = self._mp.propagate(graph)
        result = {}
        for node_id, agg_features in aggregated.items():
            output = {}
            for in_feat, out_weights in weight_matrix.items():
                if in_feat in agg_features:
                    for out_feat, w in out_weights.items():
                        output[out_feat] = output.get(out_feat, 0.0) + agg_features[in_feat] * w
            result[node_id] = output
        return result
