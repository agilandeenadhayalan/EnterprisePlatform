"""
Domain models for the Alerting service.
"""


class AlertRule:
    """An alert rule definition."""

    def __init__(
        self,
        id: str,
        name: str,
        severity: str,
        condition_type: str,
        condition_config: dict,
        channel: str,
        is_active: bool = True,
        created_at: str = "2026-03-01T00:00:00Z",
        updated_at: str = "2026-03-01T00:00:00Z",
    ):
        self.id = id
        self.name = name
        self.severity = severity
        self.condition_type = condition_type
        self.condition_config = condition_config
        self.channel = channel
        self.is_active = is_active
        self.created_at = created_at
        self.updated_at = updated_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "severity": self.severity,
            "condition_type": self.condition_type,
            "condition_config": self.condition_config,
            "channel": self.channel,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class AlertEvent:
    """An alert event (fired, resolved, silenced, acknowledged)."""

    def __init__(
        self,
        id: str,
        rule_id: str,
        rule_name: str,
        severity: str,
        status: str,
        fired_at: str,
        resolved_at: str | None = None,
        acknowledged_by: str | None = None,
        message: str = "",
    ):
        self.id = id
        self.rule_id = rule_id
        self.rule_name = rule_name
        self.severity = severity
        self.status = status
        self.fired_at = fired_at
        self.resolved_at = resolved_at
        self.acknowledged_by = acknowledged_by
        self.message = message

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "severity": self.severity,
            "status": self.status,
            "fired_at": self.fired_at,
            "resolved_at": self.resolved_at,
            "acknowledged_by": self.acknowledged_by,
            "message": self.message,
        }


class AlertRouting:
    """Routing configuration for alert delivery."""

    def __init__(
        self,
        id: str,
        channel: str,
        severity_filter: list[str],
        endpoint: str,
        is_active: bool = True,
    ):
        self.id = id
        self.channel = channel
        self.severity_filter = severity_filter
        self.endpoint = endpoint
        self.is_active = is_active

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "channel": self.channel,
            "severity_filter": self.severity_filter,
            "endpoint": self.endpoint,
            "is_active": self.is_active,
        }
