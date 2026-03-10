"""
M33: Fraud Detection — Anomaly detection, transaction graph analysis,
and fraud scoring pipelines.

This module covers how ride-hailing and payment platforms detect fraudulent
activity using statistical anomaly detection, graph-based pattern finding,
and multi-signal scoring pipelines.
"""

from .anomaly_detectors import ZScoreDetector, SimplifiedIsolationForest, SimplifiedLOF, EnsembleDetector
from .graph_analysis import TransactionNode, TransactionEdge, TransactionGraph, SuspiciousPatternFinder, SimplePageRank
from .fraud_scorer import RiskScore, RuleBasedScorer, MLBasedScorer, ScoreCalibrator, FraudScoringPipeline
