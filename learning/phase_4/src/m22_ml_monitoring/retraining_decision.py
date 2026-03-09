"""
Retraining Decision Engine -- Combines drift signals into actionable decisions.

WHY THIS MATTERS:
In production ML, multiple monitoring signals fire independently: data drift,
concept drift, feature importance shifts, and performance degradation. An
engineer needs a unified decision framework that weighs these signals and
recommends a clear action: retrain now, schedule retraining, keep monitoring,
or do nothing.

This engine codifies retraining heuristics into a deterministic rule-based
system, reducing alert fatigue and ensuring consistent responses to drift.
"""


class RetrainingDecisionEngine:
    """Combines multiple drift signals into a retraining recommendation.

    Decision logic:
      1. CRITICAL: performance degradation > 20% OR data drift > 2x threshold
      2. HIGH: concept drift detected AND (data drift > threshold OR importance drift)
      3. MEDIUM: any single strong signal (data drift, importance drift)
      4. LOW/NONE: all signals below thresholds

    WHY A DECISION ENGINE:
    Individual drift detectors produce noisy signals. A decision engine
    applies business logic to combine signals, preventing unnecessary
    retraining (expensive) while catching real degradation (critical).
    """

    def __init__(
        self,
        data_drift_threshold: float = 0.25,
        concept_drift_threshold: float = 0.1,
        importance_drift_threshold: float = 0.3,
    ):
        self.data_drift_threshold = data_drift_threshold
        self.concept_drift_threshold = concept_drift_threshold
        self.importance_drift_threshold = importance_drift_threshold

    def evaluate(
        self,
        data_drift_score: float,
        concept_drift_detected: bool,
        importance_correlation: float,
        performance_degradation_pct: float,
    ) -> dict:
        """Evaluate all drift signals and recommend an action.

        Args:
            data_drift_score: PSI or similar score (higher = more drift)
            concept_drift_detected: Whether concept drift was detected
            importance_correlation: Spearman correlation of feature importances
                                   (1.0 = no change, 0.0 = completely changed)
            performance_degradation_pct: Percentage drop in primary metric
                                         (e.g., 15.0 means 15% worse)

        Returns:
            dict with:
              - action: "retrain_now" | "schedule" | "monitor" | "no_action"
              - urgency: "critical" | "high" | "medium" | "low"
              - reasons: list[str] explaining the decision
        """
        reasons: list[str] = []

        # Assess individual signals
        severe_data_drift = data_drift_score > 2 * self.data_drift_threshold
        data_drift = data_drift_score > self.data_drift_threshold
        importance_drift = importance_correlation < (1.0 - self.importance_drift_threshold)
        severe_performance_drop = performance_degradation_pct > 20.0
        moderate_performance_drop = performance_degradation_pct > 10.0

        # Collect reasons
        if severe_data_drift:
            reasons.append(
                f"Severe data drift detected (PSI={data_drift_score:.3f}, "
                f"threshold={self.data_drift_threshold:.3f})"
            )
        elif data_drift:
            reasons.append(
                f"Data drift detected (PSI={data_drift_score:.3f})"
            )

        if concept_drift_detected:
            reasons.append("Concept drift detected: error distribution has shifted")

        if importance_drift:
            reasons.append(
                f"Feature importance ranking changed "
                f"(correlation={importance_correlation:.3f})"
            )

        if severe_performance_drop:
            reasons.append(
                f"Severe performance degradation: {performance_degradation_pct:.1f}% drop"
            )
        elif moderate_performance_drop:
            reasons.append(
                f"Moderate performance degradation: {performance_degradation_pct:.1f}% drop"
            )

        # Decision logic -- most urgent first
        if severe_performance_drop or severe_data_drift:
            return {
                "action": "retrain_now",
                "urgency": "critical",
                "reasons": reasons if reasons else ["Critical threshold exceeded"],
            }

        if concept_drift_detected and (data_drift or importance_drift):
            return {
                "action": "retrain_now",
                "urgency": "high",
                "reasons": reasons,
            }

        if concept_drift_detected or (data_drift and moderate_performance_drop):
            return {
                "action": "schedule",
                "urgency": "high",
                "reasons": reasons,
            }

        if data_drift or importance_drift:
            return {
                "action": "schedule",
                "urgency": "medium",
                "reasons": reasons,
            }

        if moderate_performance_drop:
            return {
                "action": "monitor",
                "urgency": "medium",
                "reasons": reasons,
            }

        if not reasons:
            reasons.append("All signals within normal range")

        return {
            "action": "no_action",
            "urgency": "low",
            "reasons": reasons,
        }
