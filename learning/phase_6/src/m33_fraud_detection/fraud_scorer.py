"""
Fraud Scoring Pipeline — Rules, ML scoring, calibration, and pipeline.

WHY THIS MATTERS:
Production fraud detection combines multiple signals:
  1. Rule-based scoring catches known patterns (e.g., amount > $10k).
  2. ML-based scoring catches statistical anomalies.
  3. Graph-based scoring catches network patterns.
  4. Score calibration ensures scores map to real fraud probabilities.

The pipeline combines all these into a single RiskScore that determines
whether to flag, block, or allow a transaction.
"""

import math


class RiskScore:
    """A fraud risk score for a transaction.

    Contains the score (0-1), contributing factors, and whether the
    transaction was flagged for review.
    """

    def __init__(self, transaction_id: str, score: float, factors: dict = None, flagged: bool = False):
        self.transaction_id = transaction_id
        self.score = min(1.0, max(0.0, score))
        self.factors = factors or {}
        self.flagged = flagged

    def to_dict(self) -> dict:
        """Serialize the risk score."""
        return {
            "transaction_id": self.transaction_id,
            "score": self.score,
            "factors": self.factors,
            "flagged": self.flagged,
        }


class RuleBasedScorer:
    """Score transactions using predefined rules.

    Each rule is a function that takes a transaction dict and returns
    True if the rule matches. Rules have weights that determine their
    contribution to the overall score.

    Example rules:
      - "high_amount": transaction["amount"] > 10000
      - "new_account": transaction["account_age_days"] < 7
    """

    def __init__(self):
        self._rules: list[tuple[str, callable, float]] = []

    def add_rule(self, name: str, check_fn: callable, weight: float = 1.0) -> None:
        """Add a rule with a name, check function, and weight."""
        self._rules.append((name, check_fn, weight))

    def score(self, transaction: dict) -> float:
        """Compute weighted fraction of rules that match.

        Returns a score in [0, 1] where 1 means all rules matched.
        """
        if not self._rules:
            return 0.0

        total_weight = sum(w for _, _, w in self._rules)
        if total_weight == 0:
            return 0.0

        matched_weight = 0.0
        for name, check_fn, weight in self._rules:
            try:
                if check_fn(transaction):
                    matched_weight += weight
            except (KeyError, TypeError):
                continue

        return matched_weight / total_weight

    def matched_rules(self, transaction: dict) -> list[str]:
        """Return names of rules that matched the transaction."""
        matched = []
        for name, check_fn, _ in self._rules:
            try:
                if check_fn(transaction):
                    matched.append(name)
            except (KeyError, TypeError):
                continue
        return matched


class MLBasedScorer:
    """Feature-based fraud scorer using centroid distance.

    A simplified ML-like approach: compute the centroid (mean feature
    vector) of known fraud cases and known legitimate cases, then score
    new transactions by their relative distance to each centroid.

    Score = distance_to_legit / (distance_to_fraud + distance_to_legit)
    High score means closer to fraud centroid.
    """

    def __init__(self):
        self._fraud_centroid: list[float] = []
        self._legit_centroid: list[float] = []
        self._fitted = False

    def fit(self, features: list[list[float]], labels: list[int]) -> None:
        """Compute centroids for fraud (label=1) and legit (label=0) cases.

        Args:
            features: list of feature vectors.
            labels: list of labels (0=legit, 1=fraud).
        """
        if len(features) != len(labels):
            raise ValueError("features and labels must have the same length")

        fraud_features = [f for f, l in zip(features, labels) if l == 1]
        legit_features = [f for f, l in zip(features, labels) if l == 0]

        if not fraud_features:
            raise ValueError("Need at least one fraud example")
        if not legit_features:
            raise ValueError("Need at least one legitimate example")

        n_dims = len(features[0])
        self._fraud_centroid = [
            sum(f[d] for f in fraud_features) / len(fraud_features) for d in range(n_dims)
        ]
        self._legit_centroid = [
            sum(f[d] for f in legit_features) / len(legit_features) for d in range(n_dims)
        ]
        self._fitted = True

    def score(self, features: list[float]) -> float:
        """Score a transaction by its relative distance to centroids.

        Returns a value in [0, 1] where 1 means very close to fraud
        centroid and far from legit centroid.
        """
        if not self._fitted:
            raise ValueError("Scorer not fitted — call fit() first")

        dist_fraud = self._euclidean(features, self._fraud_centroid)
        dist_legit = self._euclidean(features, self._legit_centroid)
        total = dist_fraud + dist_legit

        if total == 0:
            return 0.5
        return dist_legit / total

    @staticmethod
    def _euclidean(a: list[float], b: list[float]) -> float:
        return math.sqrt(sum((ai - bi) ** 2 for ai, bi in zip(a, b)))


class ScoreCalibrator:
    """Platt scaling — calibrate raw scores to probabilities.

    Raw fraud scores from ML models are not well-calibrated probabilities.
    Platt scaling fits a sigmoid function: P(fraud) = 1 / (1 + exp(-(a*s + b)))
    to map raw scores to calibrated probabilities.

    This is a simplified version using least-squares-style fitting.
    """

    def __init__(self):
        self._a: float = 1.0
        self._b: float = 0.0
        self._fitted = False

    def fit(self, scores: list[float], labels: list[int]) -> None:
        """Fit sigmoid parameters a and b from scores and labels.

        Uses a simple grid search to find a and b that minimize the
        binary cross-entropy loss. Production systems use Newton's method.
        """
        if len(scores) != len(labels):
            raise ValueError("scores and labels must have the same length")

        best_loss = float("inf")
        best_a, best_b = 1.0, 0.0

        for a in [x * 0.5 for x in range(-10, 21)]:
            for b in [x * 0.5 for x in range(-10, 11)]:
                loss = 0.0
                for s, l in zip(scores, labels):
                    p = 1.0 / (1.0 + math.exp(-(a * s + b)))
                    p = max(1e-7, min(1 - 1e-7, p))
                    loss -= l * math.log(p) + (1 - l) * math.log(1 - p)
                if loss < best_loss:
                    best_loss = loss
                    best_a, best_b = a, b

        self._a = best_a
        self._b = best_b
        self._fitted = True

    def calibrate(self, score: float) -> float:
        """Apply sigmoid calibration to a raw score.

        Returns a calibrated probability in [0, 1].
        """
        if not self._fitted:
            raise ValueError("Calibrator not fitted — call fit() first")
        z = self._a * score + self._b
        # Clamp to avoid overflow
        z = max(-500, min(500, z))
        return 1.0 / (1.0 + math.exp(-z))


class FraudScoringPipeline:
    """Combines rule-based, ML-based, and optional graph-based scoring.

    The final score is a weighted combination of individual scores.
    A transaction is flagged if the combined score exceeds a threshold.
    """

    def __init__(
        self,
        rule_scorer: RuleBasedScorer = None,
        ml_scorer: MLBasedScorer = None,
        rule_weight: float = 0.4,
        ml_weight: float = 0.6,
        flag_threshold: float = 0.5,
    ):
        self._rule_scorer = rule_scorer
        self._ml_scorer = ml_scorer
        self._rule_weight = rule_weight
        self._ml_weight = ml_weight
        self._flag_threshold = flag_threshold

    def score_transaction(self, transaction: dict) -> RiskScore:
        """Score a transaction through the full pipeline.

        Combines rule-based and ML-based scores with configurable weights.

        transaction dict should contain:
          - "id": transaction identifier
          - "features": list of numeric features (for ML scorer)
          - Other fields checked by rule-based scorer
        """
        factors = {}
        total_score = 0.0
        total_weight = 0.0

        # Rule-based scoring
        if self._rule_scorer:
            rule_score = self._rule_scorer.score(transaction)
            factors["rule_score"] = rule_score
            factors["matched_rules"] = self._rule_scorer.matched_rules(transaction)
            total_score += rule_score * self._rule_weight
            total_weight += self._rule_weight

        # ML-based scoring
        if self._ml_scorer and "features" in transaction:
            try:
                ml_score = self._ml_scorer.score(transaction["features"])
                factors["ml_score"] = ml_score
                total_score += ml_score * self._ml_weight
                total_weight += self._ml_weight
            except ValueError:
                pass

        # Normalize
        if total_weight > 0:
            combined = total_score / total_weight
        else:
            combined = 0.0

        flagged = combined >= self._flag_threshold
        txn_id = transaction.get("id", "unknown")

        return RiskScore(
            transaction_id=txn_id,
            score=combined,
            factors=factors,
            flagged=flagged,
        )
