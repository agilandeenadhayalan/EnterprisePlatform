"""
M31: ETA Prediction — Graph networks, road modeling, and arrival time estimation.

This module covers the core algorithms behind ride-hailing ETA systems:
graph neural network primitives for learning road embeddings, road network
modeling with congestion-aware routing, and multiple ETA prediction strategies
from simple historical averages to graph-based approaches.
"""

from .graph_networks import GraphNode, GraphEdge, Graph, MessagePassing, GraphConvolution
from .road_network import CongestionLevel, RoadSegment, SpeedProfile, Intersection, RoadNetwork
from .eta_models import BaseETAModel, HistoricalAverageETA, SegmentBasedETA, GraphBasedETA
from .route_features import RouteFeatureExtractor
