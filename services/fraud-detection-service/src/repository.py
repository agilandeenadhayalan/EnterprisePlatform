"""
In-memory fraud detection repository with pre-seeded data.
"""

import uuid
from datetime import datetime, timezone

from models import FraudAlert, FraudRule, TransactionScore


class FraudDetectionRepository:
    """In-memory store for fraud alerts, rules, and transaction scores."""

    def __init__(self, seed: bool = False):
        self.alerts: list[FraudAlert] = []
        self.rules: dict[str, FraudRule] = {}
        self.scores: list[TransactionScore] = []
        if seed:
            self._seed()

    def _seed(self):
        now = datetime.now(timezone.utc).isoformat()

        rules = [
            FraudRule("rule-001", "velocity_check", "velocity", 10.0, True, {"window_minutes": 5, "max_transactions": 10}, now),
            FraudRule("rule-002", "amount_threshold", "threshold", 5000.0, True, {"max_amount": 5000, "currency": "USD"}, now),
            FraudRule("rule-003", "geo_anomaly", "geo", 0.8, True, {"max_distance_km": 500, "time_window_hours": 1}, now),
            FraudRule("rule-004", "device_fingerprint", "fingerprint", 0.7, True, {"check_browser": True, "check_ip": True}, now),
            FraudRule("rule-005", "graph_pattern", "graph", 0.85, True, {"min_connections": 3, "depth": 2}, now),
            FraudRule("rule-006", "behavior_change", "behavior", 0.75, False, {"lookback_days": 30, "deviation_threshold": 2.0}, now),
        ]
        for r in rules:
            self.rules[r.id] = r

        alerts = [
            FraudAlert("alert-001", "txn-101", "user-A", 0.92, "velocity", "open", {"transactions_in_window": 15}, now),
            FraudAlert("alert-002", "txn-102", "user-B", 0.88, "amount", "open", {"amount": 8500, "threshold": 5000}, now),
            FraudAlert("alert-003", "txn-103", "user-C", 0.95, "geo", "investigating", {"distance_km": 1200, "time_hours": 0.5}, now),
            FraudAlert("alert-004", "txn-104", "user-D", 0.78, "fingerprint", "investigating", {"new_device": True}, now),
            FraudAlert("alert-005", "txn-105", "user-A", 0.85, "velocity", "resolved", {"transactions_in_window": 12}, now),
            FraudAlert("alert-006", "txn-106", "user-E", 0.72, "amount", "resolved", {"amount": 6200, "threshold": 5000}, now),
            FraudAlert("alert-007", "txn-107", "user-F", 0.91, "graph", "open", {"connected_flagged_users": 4}, now),
            FraudAlert("alert-008", "txn-108", "user-G", 0.68, "behavior", "resolved", {"deviation_score": 2.5}, now),
        ]
        self.alerts.extend(alerts)

        scores = [
            TransactionScore("txn-101", {"velocity": 0.95, "amount": 0.3, "geo": 0.1}, 0.92, True),
            TransactionScore("txn-102", {"velocity": 0.2, "amount": 0.95, "geo": 0.5}, 0.88, True),
            TransactionScore("txn-103", {"velocity": 0.1, "amount": 0.4, "geo": 0.98}, 0.95, True),
            TransactionScore("txn-109", {"velocity": 0.1, "amount": 0.2, "geo": 0.1}, 0.15, False),
            TransactionScore("txn-110", {"velocity": 0.05, "amount": 0.1, "geo": 0.05}, 0.08, False),
        ]
        self.scores.extend(scores)

    # ── Alerts ──

    def list_alerts(self, status: str | None = None, alert_type: str | None = None) -> list[FraudAlert]:
        result = list(self.alerts)
        if status:
            result = [a for a in result if a.status == status]
        if alert_type:
            result = [a for a in result if a.alert_type == alert_type]
        return result

    def get_alert(self, alert_id: str) -> FraudAlert | None:
        for a in self.alerts:
            if a.id == alert_id:
                return a
        return None

    def resolve_alert(self, alert_id: str) -> FraudAlert | None:
        for a in self.alerts:
            if a.id == alert_id:
                a.status = "resolved"
                a.resolved_at = datetime.now(timezone.utc).isoformat()
                return a
        return None

    # ── Scoring ──

    def score_transaction(self, data: dict) -> TransactionScore:
        amount = data.get("amount", 0)
        # Simple scoring based on amount
        amount_score = min(amount / 10000.0, 1.0)
        velocity_score = 0.3 if data.get("features", {}).get("rapid", False) else 0.1
        geo_score = 0.5 if data.get("features", {}).get("foreign", False) else 0.1
        scores = {"velocity": velocity_score, "amount": amount_score, "geo": geo_score}
        ensemble = max(scores.values()) * 0.6 + sum(scores.values()) / len(scores) * 0.4
        ensemble = round(min(ensemble, 1.0), 4)
        flagged = ensemble > 0.5

        ts = TransactionScore(
            transaction_id=data["transaction_id"],
            scores=scores,
            ensemble_score=ensemble,
            flagged=flagged,
        )
        self.scores.append(ts)
        return ts

    # ── Rules ──

    def list_rules(self) -> list[FraudRule]:
        return list(self.rules.values())

    def create_rule(self, data: dict) -> FraudRule:
        rule_id = f"rule-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()
        rule = FraudRule(
            id=rule_id,
            name=data["name"],
            rule_type=data["rule_type"],
            threshold=data["threshold"],
            is_active=data.get("is_active", True),
            config=data.get("config", {}),
            created_at=now,
        )
        self.rules[rule.id] = rule
        return rule

    def toggle_rule(self, rule_id: str) -> FraudRule | None:
        rule = self.rules.get(rule_id)
        if rule:
            rule.is_active = not rule.is_active
        return rule

    # ── Graph Analysis ──

    def analyze_graph(self, user_ids: list[str]) -> dict:
        patterns = []
        if len(user_ids) >= 2:
            patterns.append({"type": "shared_device", "users": user_ids[:2], "confidence": 0.82})
        if len(user_ids) >= 3:
            patterns.append({"type": "circular_transfers", "users": user_ids[:3], "confidence": 0.91})
        risk_level = "high" if patterns else "low"
        return {
            "user_ids": user_ids,
            "suspicious_patterns": patterns,
            "risk_level": risk_level,
        }

    # ── Stats ──

    def get_stats(self) -> dict:
        by_status: dict[str, int] = {}
        by_type: dict[str, int] = {}
        total_risk = 0.0
        for a in self.alerts:
            by_status[a.status] = by_status.get(a.status, 0) + 1
            by_type[a.alert_type] = by_type.get(a.alert_type, 0) + 1
            total_risk += a.risk_score
        avg_risk = total_risk / len(self.alerts) if self.alerts else 0.0
        return {
            "total_alerts": len(self.alerts),
            "by_status": by_status,
            "by_type": by_type,
            "avg_risk_score": round(avg_risk, 4),
        }


REPO_CLASS = FraudDetectionRepository
repo = FraudDetectionRepository(seed=True)
