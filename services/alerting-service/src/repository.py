"""
In-memory alerting repository with pre-seeded data.
"""

import uuid
from datetime import datetime, timezone

from models import AlertRule, AlertEvent, AlertRouting


class AlertingRepository:
    """In-memory store for alert rules, events, and routing."""

    def __init__(self, seed: bool = False):
        self.rules: dict[str, AlertRule] = {}
        self.events: list[AlertEvent] = []
        self.routing_rules: list[AlertRouting] = []
        if seed:
            self._seed()

    def _seed(self):
        now = datetime.now(timezone.utc).isoformat()

        rules = [
            AlertRule("rule-001", "CPU High", "critical", "threshold", {"metric": "cpu", "operator": ">", "value": 90}, "pagerduty", True, now, now),
            AlertRule("rule-002", "Error Rate Spike", "critical", "rate", {"metric": "error_rate", "operator": ">", "value": 5}, "slack", True, now, now),
            AlertRule("rule-003", "Disk Usage", "warning", "threshold", {"metric": "disk", "operator": ">", "value": 85}, "email", True, now, now),
            AlertRule("rule-004", "Latency P99", "warning", "threshold", {"metric": "p99", "operator": ">", "value": 500}, "slack", True, now, now),
            AlertRule("rule-005", "Memory Pressure", "warning", "threshold", {"metric": "memory", "operator": ">", "value": 80}, "email", True, now, now),
            AlertRule("rule-006", "Pod Restart Loop", "critical", "count", {"metric": "restarts", "operator": ">", "value": 5}, "pagerduty", True, now, now),
            AlertRule("rule-007", "SSL Cert Expiry", "info", "threshold", {"metric": "days", "operator": "<", "value": 30}, "email", True, now, now),
            AlertRule("rule-008", "DB Connection Pool", "warning", "threshold", {"metric": "pool", "operator": ">", "value": 90}, "slack", True, now, now),
        ]
        for r in rules:
            self.rules[r.id] = r

        events = [
            AlertEvent("evt-001", "rule-001", "CPU High", "critical", "firing", now, None, None, "CPU usage at 95% on auth-service"),
            AlertEvent("evt-002", "rule-002", "Error Rate Spike", "critical", "firing", now, None, None, "Error rate at 8.2% on payment-service"),
            AlertEvent("evt-003", "rule-006", "Pod Restart Loop", "critical", "firing", now, None, None, "Pod restart count 7 on user-service"),
            AlertEvent("evt-004", "rule-003", "Disk Usage", "warning", "resolved", now, now, None, "Disk usage back to 72%"),
            AlertEvent("evt-005", "rule-005", "Memory Pressure", "warning", "resolved", now, now, None, "Memory usage back to 65%"),
            AlertEvent("evt-006", "rule-004", "Latency P99", "warning", "acknowledged", now, None, "oncall-engineer", "P99 latency at 620ms"),
        ]
        self.events.extend(events)

        routing = [
            AlertRouting("route-001", "email", ["info", "warning"], "ops@example.com", True),
            AlertRouting("route-002", "slack", ["warning", "critical"], "#alerts", True),
            AlertRouting("route-003", "pagerduty", ["critical"], "service-key", True),
            AlertRouting("route-004", "webhook", ["info", "warning", "critical"], "https://hooks.example.com", True),
        ]
        self.routing_rules.extend(routing)

    # ── Rules ──

    def list_rules(self) -> list[AlertRule]:
        return list(self.rules.values())

    def get_rule(self, rule_id: str) -> AlertRule | None:
        return self.rules.get(rule_id)

    def create_rule(self, data: dict) -> AlertRule:
        rule_id = f"rule-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()
        rule = AlertRule(
            id=rule_id,
            name=data["name"],
            severity=data["severity"],
            condition_type=data["condition_type"],
            condition_config=data.get("condition_config", {}),
            channel=data["channel"],
            is_active=data.get("is_active", True),
            created_at=now,
            updated_at=now,
        )
        self.rules[rule.id] = rule
        return rule

    def silence_rule(self, rule_id: str) -> AlertRule | None:
        rule = self.rules.get(rule_id)
        if rule:
            rule.is_active = False
            rule.updated_at = datetime.now(timezone.utc).isoformat()
        return rule

    # ── Events ──

    def fire_alert(self, rule_id: str, message: str) -> AlertEvent | None:
        rule = self.rules.get(rule_id)
        if not rule:
            return None
        now = datetime.now(timezone.utc).isoformat()
        event = AlertEvent(
            id=f"evt-{uuid.uuid4().hex[:8]}",
            rule_id=rule.id,
            rule_name=rule.name,
            severity=rule.severity,
            status="firing",
            fired_at=now,
            message=message,
        )
        self.events.append(event)
        return event

    def resolve_event(self, event_id: str) -> AlertEvent | None:
        for evt in self.events:
            if evt.id == event_id:
                evt.status = "resolved"
                evt.resolved_at = datetime.now(timezone.utc).isoformat()
                return evt
        return None

    def acknowledge_event(self, event_id: str, acknowledged_by: str) -> AlertEvent | None:
        for evt in self.events:
            if evt.id == event_id:
                evt.status = "acknowledged"
                evt.acknowledged_by = acknowledged_by
                return evt
        return None

    def list_events(self) -> list[AlertEvent]:
        return list(self.events)

    # ── Routing ──

    def list_routing(self) -> list[AlertRouting]:
        return list(self.routing_rules)

    # ── Stats ──

    def get_stats(self) -> dict:
        firing = sum(1 for e in self.events if e.status == "firing")
        resolved = sum(1 for e in self.events if e.status == "resolved")
        by_severity = {}
        for r in self.rules.values():
            by_severity[r.severity] = by_severity.get(r.severity, 0) + 1
        return {
            "total_rules": len(self.rules),
            "active_rules": sum(1 for r in self.rules.values() if r.is_active),
            "firing_alerts": firing,
            "resolved_alerts": resolved,
            "by_severity": by_severity,
        }


REPO_CLASS = AlertingRepository
repo = AlertingRepository(seed=True)
