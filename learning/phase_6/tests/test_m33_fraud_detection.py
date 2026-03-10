"""
Tests for M33: Fraud Detection — Anomaly detection, transaction graph
analysis, and fraud scoring pipelines.
"""

import math
import pytest

from m33_fraud_detection.anomaly_detectors import (
    ZScoreDetector,
    SimplifiedIsolationForest,
    SimplifiedLOF,
    EnsembleDetector,
)
from m33_fraud_detection.graph_analysis import (
    TransactionNode,
    TransactionEdge,
    TransactionGraph,
    SuspiciousPatternFinder,
    SimplePageRank,
)
from m33_fraud_detection.fraud_scorer import (
    RiskScore,
    RuleBasedScorer,
    MLBasedScorer,
    ScoreCalibrator,
    FraudScoringPipeline,
)


# ── ZScoreDetector ──


class TestZScoreDetector:
    def test_fit(self):
        """Detector stores mean and std after fit."""
        d = ZScoreDetector()
        d.fit([10, 20, 30, 40, 50])
        assert d._mean == pytest.approx(30.0)
        assert d._std > 0

    def test_score_at_mean(self):
        """Z-score at the mean is 0."""
        d = ZScoreDetector()
        d.fit([10, 20, 30, 40, 50])
        assert d.score(30.0) == pytest.approx(0.0)

    def test_score_one_std(self):
        """Z-score at mean + std is 1.0."""
        d = ZScoreDetector()
        d.fit([10, 20, 30, 40, 50])
        score = d.score(30.0 + d._std)
        assert score == pytest.approx(1.0)

    def test_is_anomaly_true(self):
        """Value far from mean is anomalous."""
        d = ZScoreDetector()
        d.fit([10, 20, 30, 40, 50])
        assert d.is_anomaly(200.0) is True

    def test_is_anomaly_false(self):
        """Value near mean is not anomalous."""
        d = ZScoreDetector()
        d.fit([10, 20, 30, 40, 50])
        assert d.is_anomaly(30.0) is False

    def test_fit_empty_raises(self):
        """Fitting with empty data raises ValueError."""
        d = ZScoreDetector()
        with pytest.raises(ValueError):
            d.fit([])

    def test_score_not_fitted(self):
        """Scoring without fit raises ValueError."""
        d = ZScoreDetector()
        with pytest.raises(ValueError, match="not fitted"):
            d.score(10.0)

    def test_score_zero_std(self):
        """Constant data gives zero std, score returns 0."""
        d = ZScoreDetector()
        d.fit([5, 5, 5, 5])
        assert d.score(5.0) == 0.0
        assert d.score(100.0) == 0.0

    def test_custom_threshold(self):
        """Custom threshold affects is_anomaly."""
        d = ZScoreDetector()
        d.fit([10, 20, 30, 40, 50])
        # With threshold=1.0, values 1 std away are anomalous
        assert d.is_anomaly(30.0 + d._std + 1, threshold=1.0) is True


# ── SimplifiedIsolationForest ──


class TestSimplifiedIsolationForest:
    def test_fit(self):
        """Isolation forest fits without error."""
        ifo = SimplifiedIsolationForest(n_trees=5, seed=42)
        data = [[x, x] for x in range(50)]
        ifo.fit(data)
        assert ifo._fitted is True

    def test_score_normal_point(self):
        """Normal points have score near 0.5."""
        ifo = SimplifiedIsolationForest(n_trees=20, seed=42)
        data = [[x, x] for x in range(100)]
        ifo.fit(data)
        score = ifo.score([50, 50])
        assert 0.3 < score < 0.7

    def test_score_anomaly(self):
        """Outlier has higher score than normal point."""
        ifo = SimplifiedIsolationForest(n_trees=20, seed=42)
        data = [[x, x] for x in range(100)]
        ifo.fit(data)
        normal_score = ifo.score([50, 50])
        anomaly_score = ifo.score([1000, 1000])
        assert anomaly_score > normal_score

    def test_is_anomaly(self):
        """Extreme outlier is detected as anomalous."""
        ifo = SimplifiedIsolationForest(n_trees=20, seed=42)
        data = [[x, x] for x in range(100)]
        ifo.fit(data)
        assert ifo.is_anomaly([1000, 1000]) is True

    def test_fit_empty_raises(self):
        """Fitting with empty data raises ValueError."""
        ifo = SimplifiedIsolationForest()
        with pytest.raises(ValueError):
            ifo.fit([])

    def test_score_not_fitted(self):
        """Scoring without fit raises ValueError."""
        ifo = SimplifiedIsolationForest()
        with pytest.raises(ValueError, match="not fitted"):
            ifo.score([1, 2])


# ── SimplifiedLOF ──


class TestSimplifiedLOF:
    def test_fit(self):
        """LOF fits without error."""
        lof = SimplifiedLOF(k=3)
        data = [[x, 0] for x in range(20)]
        lof.fit(data)
        assert lof._fitted is True

    def test_score_normal(self):
        """Normal point in dense region has low LOF score."""
        lof = SimplifiedLOF(k=3)
        data = [[x, 0] for x in range(20)]
        lof.fit(data)
        score = lof.score([10, 0])
        assert score < 2.0

    def test_score_outlier(self):
        """Outlier in sparse region has high LOF score."""
        lof = SimplifiedLOF(k=3)
        data = [[x, 0] for x in range(20)]
        lof.fit(data)
        score = lof.score([100, 0])
        assert score > 1.0

    def test_is_anomaly(self):
        """Outlier flagged as anomalous."""
        lof = SimplifiedLOF(k=3)
        data = [[x, 0] for x in range(20)]
        lof.fit(data)
        assert lof.is_anomaly([100, 0]) is True

    def test_fit_empty_raises(self):
        """Empty data raises ValueError."""
        lof = SimplifiedLOF()
        with pytest.raises(ValueError):
            lof.fit([])

    def test_score_not_fitted(self):
        """Scoring without fit raises ValueError."""
        lof = SimplifiedLOF()
        with pytest.raises(ValueError, match="not fitted"):
            lof.score([1, 2])


# ── EnsembleDetector ──


class TestEnsembleDetector:
    def test_score_single_detector(self):
        """Ensemble with one detector returns that detector's score."""
        zsd = ZScoreDetector()
        zsd.fit([10, 20, 30, 40, 50])
        ens = EnsembleDetector()
        ens.add_detector(zsd, weight=1.0)
        assert ens.score(30.0) == pytest.approx(zsd.score(30.0))

    def test_score_weighted_average(self):
        """Ensemble returns weighted average of detector scores."""
        d1 = ZScoreDetector()
        d1.fit([10, 20, 30, 40, 50])
        d2 = ZScoreDetector()
        d2.fit([100, 200, 300, 400, 500])
        ens = EnsembleDetector()
        ens.add_detector(d1, weight=1.0)
        ens.add_detector(d2, weight=1.0)
        s1 = d1.score(30.0)
        s2 = d2.score(30.0)
        assert ens.score(30.0) == pytest.approx((s1 + s2) / 2.0)

    def test_is_anomaly_majority(self):
        """Majority vote determines ensemble anomaly flag."""
        d1 = ZScoreDetector()
        d1.fit([10, 20, 30, 40, 50])
        d2 = ZScoreDetector()
        d2.fit([10, 20, 30, 40, 50])
        ens = EnsembleDetector()
        ens.add_detector(d1, weight=1.0)
        ens.add_detector(d2, weight=1.0)
        # Both should agree on anomaly status
        assert ens.is_anomaly(30.0) is False
        assert ens.is_anomaly(200.0) is True

    def test_empty_ensemble_raises(self):
        """Empty ensemble raises ValueError."""
        ens = EnsembleDetector()
        with pytest.raises(ValueError, match="No detectors"):
            ens.score(10.0)


# ── TransactionGraph ──


class TestTransactionGraph:
    def test_add_node(self):
        """Graph can add and retrieve nodes."""
        g = TransactionGraph()
        g.add_node(TransactionNode("u1", "user", {"name": "Alice"}))
        assert g.get_node("u1").node_type == "user"

    def test_add_edge(self):
        """Graph can add transaction edges."""
        g = TransactionGraph()
        g.add_node(TransactionNode("u1"))
        g.add_node(TransactionNode("u2"))
        g.add_edge(TransactionEdge("u1", "u2", 100.0))
        assert len(g.get_edges("u1")) == 1

    def test_add_edge_missing_node(self):
        """Adding edge with missing node raises ValueError."""
        g = TransactionGraph()
        g.add_node(TransactionNode("u1"))
        with pytest.raises(ValueError):
            g.add_edge(TransactionEdge("u1", "u2", 100.0))

    def test_fan_out(self):
        """fan_out counts distinct outgoing targets."""
        g = TransactionGraph()
        g.add_node(TransactionNode("u1"))
        g.add_node(TransactionNode("u2"))
        g.add_node(TransactionNode("u3"))
        g.add_edge(TransactionEdge("u1", "u2", 50.0))
        g.add_edge(TransactionEdge("u1", "u3", 75.0))
        assert g.fan_out("u1") == 2

    def test_fan_in(self):
        """fan_in counts distinct incoming sources."""
        g = TransactionGraph()
        g.add_node(TransactionNode("u1"))
        g.add_node(TransactionNode("u2"))
        g.add_node(TransactionNode("u3"))
        g.add_edge(TransactionEdge("u1", "u3", 50.0))
        g.add_edge(TransactionEdge("u2", "u3", 75.0))
        assert g.fan_in("u3") == 2

    def test_fan_out_zero(self):
        """Node with no outgoing edges has fan_out 0."""
        g = TransactionGraph()
        g.add_node(TransactionNode("u1"))
        assert g.fan_out("u1") == 0

    def test_get_node_not_found(self):
        """Getting non-existent node raises KeyError."""
        g = TransactionGraph()
        with pytest.raises(KeyError):
            g.get_node("x")

    def test_node_count(self):
        """node_count tracks nodes."""
        g = TransactionGraph()
        g.add_node(TransactionNode("u1"))
        g.add_node(TransactionNode("u2"))
        assert g.node_count == 2


# ── SuspiciousPatternFinder ──


class TestSuspiciousPatternFinder:
    def test_detect_fan_out(self):
        """Detects nodes with fan_out exceeding threshold."""
        g = TransactionGraph()
        g.add_node(TransactionNode("u1"))
        for i in range(10):
            nid = f"t{i}"
            g.add_node(TransactionNode(nid))
            g.add_edge(TransactionEdge("u1", nid, 10.0))
        finder = SuspiciousPatternFinder()
        suspicious = finder.detect_fan_out(g, threshold=5)
        assert "u1" in suspicious

    def test_detect_fan_out_below_threshold(self):
        """No nodes detected when fan_out is below threshold."""
        g = TransactionGraph()
        g.add_node(TransactionNode("u1"))
        g.add_node(TransactionNode("u2"))
        g.add_edge(TransactionEdge("u1", "u2", 10.0))
        finder = SuspiciousPatternFinder()
        assert finder.detect_fan_out(g, threshold=5) == []

    def test_detect_rapid_transactions(self):
        """Detects transactions within a narrow time window."""
        g = TransactionGraph()
        g.add_node(TransactionNode("u1"))
        g.add_node(TransactionNode("u2"))
        g.add_node(TransactionNode("u3"))
        g.add_edge(TransactionEdge("u1", "u2", 10.0, "2024-01-01 10:00:00"))
        g.add_edge(TransactionEdge("u1", "u3", 20.0, "2024-01-01 10:00:30"))
        finder = SuspiciousPatternFinder()
        rapid = finder.detect_rapid_transactions(g, "u1", window_seconds=60)
        assert len(rapid) == 2

    def test_detect_rapid_transactions_none(self):
        """No rapid transactions when timestamps are spread out."""
        g = TransactionGraph()
        g.add_node(TransactionNode("u1"))
        g.add_node(TransactionNode("u2"))
        g.add_edge(TransactionEdge("u1", "u2", 10.0, "2024-01-01 10:00:00"))
        finder = SuspiciousPatternFinder()
        rapid = finder.detect_rapid_transactions(g, "u1", window_seconds=60)
        assert len(rapid) == 0

    def test_detect_round_trip(self):
        """Detects A -> B -> A money flow."""
        g = TransactionGraph()
        g.add_node(TransactionNode("u1"))
        g.add_node(TransactionNode("u2"))
        g.add_edge(TransactionEdge("u1", "u2", 100.0))
        g.add_edge(TransactionEdge("u2", "u1", 95.0))
        finder = SuspiciousPatternFinder()
        trips = finder.detect_round_trip(g)
        assert len(trips) == 1

    def test_detect_round_trip_none(self):
        """No round trip when money flows one way."""
        g = TransactionGraph()
        g.add_node(TransactionNode("u1"))
        g.add_node(TransactionNode("u2"))
        g.add_edge(TransactionEdge("u1", "u2", 100.0))
        finder = SuspiciousPatternFinder()
        assert finder.detect_round_trip(g) == []


# ── SimplePageRank ──


class TestSimplePageRank:
    def test_pagerank_uniform(self):
        """Isolated nodes get uniform PageRank."""
        g = TransactionGraph()
        g.add_node(TransactionNode("u1"))
        g.add_node(TransactionNode("u2"))
        pr = SimplePageRank(g)
        assert pr["u1"] == pytest.approx(pr["u2"], abs=0.01)

    def test_pagerank_converges(self):
        """PageRank scores sum to approximately 1."""
        g = TransactionGraph()
        for i in range(5):
            g.add_node(TransactionNode(f"u{i}"))
        g.add_edge(TransactionEdge("u0", "u1", 10.0))
        g.add_edge(TransactionEdge("u1", "u2", 10.0))
        g.add_edge(TransactionEdge("u2", "u0", 10.0))
        g.add_edge(TransactionEdge("u3", "u0", 10.0))
        g.add_edge(TransactionEdge("u4", "u0", 10.0))
        pr = SimplePageRank(g)
        total = sum(pr.values())
        assert total == pytest.approx(1.0, abs=0.05)

    def test_pagerank_popular_node(self):
        """Node with many incoming edges has higher PageRank."""
        g = TransactionGraph()
        g.add_node(TransactionNode("popular"))
        for i in range(10):
            nid = f"u{i}"
            g.add_node(TransactionNode(nid))
            g.add_edge(TransactionEdge(nid, "popular", 10.0))
        pr = SimplePageRank(g)
        # Popular node should have highest PR
        max_node = max(pr, key=pr.get)
        assert max_node == "popular"

    def test_pagerank_empty_graph(self):
        """Empty graph returns empty dict."""
        g = TransactionGraph()
        assert SimplePageRank(g) == {}


# ── RiskScore ──


class TestRiskScore:
    def test_create_risk_score(self):
        """RiskScore stores transaction_id, score, factors, flagged."""
        rs = RiskScore("t1", 0.8, {"rule": 0.5}, True)
        assert rs.transaction_id == "t1"
        assert rs.score == 0.8
        assert rs.flagged is True

    def test_score_clamped(self):
        """Score is clamped to [0, 1]."""
        rs = RiskScore("t1", 1.5)
        assert rs.score == 1.0
        rs2 = RiskScore("t2", -0.5)
        assert rs2.score == 0.0

    def test_to_dict(self):
        """to_dict returns expected keys."""
        rs = RiskScore("t1", 0.5, {"x": 1}, False)
        d = rs.to_dict()
        assert d["transaction_id"] == "t1"
        assert d["score"] == 0.5
        assert d["flagged"] is False


# ── RuleBasedScorer ──


class TestRuleBasedScorer:
    def test_add_and_score(self):
        """Rule matches produce a positive score."""
        scorer = RuleBasedScorer()
        scorer.add_rule("high_amount", lambda t: t["amount"] > 1000, weight=1.0)
        assert scorer.score({"amount": 2000}) == pytest.approx(1.0)

    def test_no_rules_zero_score(self):
        """Empty scorer returns 0."""
        scorer = RuleBasedScorer()
        assert scorer.score({}) == 0.0

    def test_partial_match(self):
        """Score reflects fraction of matched rule weight."""
        scorer = RuleBasedScorer()
        scorer.add_rule("high", lambda t: t["amount"] > 1000, weight=1.0)
        scorer.add_rule("new", lambda t: t["age"] < 7, weight=1.0)
        # Only one rule matches
        score = scorer.score({"amount": 2000, "age": 30})
        assert score == pytest.approx(0.5)

    def test_matched_rules(self):
        """matched_rules returns names of matching rules."""
        scorer = RuleBasedScorer()
        scorer.add_rule("high", lambda t: t["amount"] > 1000, weight=1.0)
        scorer.add_rule("low", lambda t: t["amount"] < 10, weight=1.0)
        matched = scorer.matched_rules({"amount": 2000})
        assert "high" in matched
        assert "low" not in matched


# ── MLBasedScorer ──


class TestMLBasedScorer:
    def test_fit_and_score(self):
        """ML scorer fits and produces scores in [0, 1]."""
        scorer = MLBasedScorer()
        features = [[1, 1], [2, 2], [10, 10], [11, 11]]
        labels = [0, 0, 1, 1]
        scorer.fit(features, labels)
        score = scorer.score([10, 10])
        assert 0 <= score <= 1

    def test_score_closer_to_fraud(self):
        """Point near fraud centroid scores higher than point near legit."""
        scorer = MLBasedScorer()
        features = [[1, 1], [2, 2], [10, 10], [11, 11]]
        labels = [0, 0, 1, 1]
        scorer.fit(features, labels)
        fraud_score = scorer.score([10, 10])
        legit_score = scorer.score([1, 1])
        assert fraud_score > legit_score

    def test_fit_no_fraud_raises(self):
        """Fitting without fraud examples raises ValueError."""
        scorer = MLBasedScorer()
        with pytest.raises(ValueError, match="fraud"):
            scorer.fit([[1, 1], [2, 2]], [0, 0])

    def test_fit_no_legit_raises(self):
        """Fitting without legit examples raises ValueError."""
        scorer = MLBasedScorer()
        with pytest.raises(ValueError, match="legitimate"):
            scorer.fit([[1, 1], [2, 2]], [1, 1])

    def test_score_not_fitted(self):
        """Scoring without fit raises ValueError."""
        scorer = MLBasedScorer()
        with pytest.raises(ValueError, match="not fitted"):
            scorer.score([1, 1])


# ── ScoreCalibrator ──


class TestScoreCalibrator:
    def test_fit_and_calibrate(self):
        """Calibrator produces values in (0, 1)."""
        cal = ScoreCalibrator()
        scores = [0.1, 0.2, 0.8, 0.9]
        labels = [0, 0, 1, 1]
        cal.fit(scores, labels)
        result = cal.calibrate(0.5)
        assert 0 < result < 1

    def test_calibrate_high_score(self):
        """High raw score maps to high calibrated probability."""
        cal = ScoreCalibrator()
        scores = [0.1, 0.2, 0.3, 0.8, 0.9, 1.0]
        labels = [0, 0, 0, 1, 1, 1]
        cal.fit(scores, labels)
        high = cal.calibrate(1.0)
        low = cal.calibrate(0.0)
        assert high > low

    def test_calibrate_not_fitted(self):
        """Calibrating without fit raises ValueError."""
        cal = ScoreCalibrator()
        with pytest.raises(ValueError, match="not fitted"):
            cal.calibrate(0.5)


# ── FraudScoringPipeline ──


class TestFraudScoringPipeline:
    def test_rule_only_pipeline(self):
        """Pipeline with only rule scorer produces RiskScore."""
        rule_scorer = RuleBasedScorer()
        rule_scorer.add_rule("high", lambda t: t["amount"] > 1000, weight=1.0)
        pipeline = FraudScoringPipeline(
            rule_scorer=rule_scorer,
            rule_weight=1.0,
            ml_weight=0.0,
            flag_threshold=0.5,
        )
        result = pipeline.score_transaction({"id": "t1", "amount": 2000})
        assert isinstance(result, RiskScore)
        assert result.flagged is True

    def test_combined_pipeline(self):
        """Pipeline combines rule and ML scores."""
        rule_scorer = RuleBasedScorer()
        rule_scorer.add_rule("high", lambda t: t["amount"] > 1000, weight=1.0)
        ml_scorer = MLBasedScorer()
        ml_scorer.fit([[1, 1], [2, 2], [10, 10], [11, 11]], [0, 0, 1, 1])
        pipeline = FraudScoringPipeline(
            rule_scorer=rule_scorer,
            ml_scorer=ml_scorer,
            rule_weight=0.4,
            ml_weight=0.6,
            flag_threshold=0.5,
        )
        result = pipeline.score_transaction({
            "id": "t1",
            "amount": 2000,
            "features": [10, 10],
        })
        assert 0 <= result.score <= 1
        assert "rule_score" in result.factors
        assert "ml_score" in result.factors

    def test_pipeline_below_threshold(self):
        """Transaction below threshold is not flagged."""
        rule_scorer = RuleBasedScorer()
        rule_scorer.add_rule("high", lambda t: t["amount"] > 1000, weight=1.0)
        pipeline = FraudScoringPipeline(
            rule_scorer=rule_scorer,
            rule_weight=1.0,
            flag_threshold=0.5,
        )
        result = pipeline.score_transaction({"id": "t1", "amount": 50})
        assert result.flagged is False

    def test_pipeline_no_scorers(self):
        """Pipeline with no scorers returns zero score."""
        pipeline = FraudScoringPipeline()
        result = pipeline.score_transaction({"id": "t1"})
        assert result.score == 0.0
        assert result.flagged is False
