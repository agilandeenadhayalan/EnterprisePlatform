"""
Domain models for the SLO Tracker service.
"""


class SloDefinition:
    """An SLO definition."""

    def __init__(
        self,
        id: str,
        service_name: str,
        slo_type: str,
        target_percentage: float,
        window_days: int,
        description: str,
        created_at: str,
    ):
        self.id = id
        self.service_name = service_name
        self.slo_type = slo_type
        self.target_percentage = target_percentage
        self.window_days = window_days
        self.description = description
        self.created_at = created_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "service_name": self.service_name,
            "slo_type": self.slo_type,
            "target_percentage": self.target_percentage,
            "window_days": self.window_days,
            "description": self.description,
            "created_at": self.created_at,
        }


class SloRecord:
    """A recorded SLO measurement for a period."""

    def __init__(
        self,
        id: str,
        slo_id: str,
        period_start: str,
        period_end: str,
        good_events: int,
        total_events: int,
        actual_percentage: float,
        error_budget_remaining: float,
    ):
        self.id = id
        self.slo_id = slo_id
        self.period_start = period_start
        self.period_end = period_end
        self.good_events = good_events
        self.total_events = total_events
        self.actual_percentage = actual_percentage
        self.error_budget_remaining = error_budget_remaining

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "slo_id": self.slo_id,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "good_events": self.good_events,
            "total_events": self.total_events,
            "actual_percentage": self.actual_percentage,
            "error_budget_remaining": self.error_budget_remaining,
        }


class BurnRateAlert:
    """A burn rate alert for an SLO."""

    def __init__(
        self,
        id: str,
        slo_id: str,
        burn_rate: float,
        threshold: float,
        is_critical: bool,
        created_at: str,
        message: str,
    ):
        self.id = id
        self.slo_id = slo_id
        self.burn_rate = burn_rate
        self.threshold = threshold
        self.is_critical = is_critical
        self.created_at = created_at
        self.message = message

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "slo_id": self.slo_id,
            "burn_rate": self.burn_rate,
            "threshold": self.threshold,
            "is_critical": self.is_critical,
            "created_at": self.created_at,
            "message": self.message,
        }
