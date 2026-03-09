"""
Domain models for the Synthetic Monitor service.
"""


class SyntheticMonitor:
    """A synthetic monitor definition."""

    def __init__(
        self,
        id: str,
        name: str,
        monitor_type: str,
        target_url: str,
        interval_seconds: int,
        timeout_seconds: int = 30,
        expected_status_code: int = 200,
        is_active: bool = True,
        created_at: str = "",
    ):
        self.id = id
        self.name = name
        self.monitor_type = monitor_type
        self.target_url = target_url
        self.interval_seconds = interval_seconds
        self.timeout_seconds = timeout_seconds
        self.expected_status_code = expected_status_code
        self.is_active = is_active
        self.created_at = created_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "monitor_type": self.monitor_type,
            "target_url": self.target_url,
            "interval_seconds": self.interval_seconds,
            "timeout_seconds": self.timeout_seconds,
            "expected_status_code": self.expected_status_code,
            "is_active": self.is_active,
            "created_at": self.created_at,
        }


class SyntheticResult:
    """A result from running a synthetic check."""

    def __init__(
        self,
        id: str,
        monitor_id: str,
        monitor_name: str,
        status_code: int,
        response_time_ms: float,
        is_success: bool,
        error_message: str | None = None,
        checked_at: str = "",
    ):
        self.id = id
        self.monitor_id = monitor_id
        self.monitor_name = monitor_name
        self.status_code = status_code
        self.response_time_ms = response_time_ms
        self.is_success = is_success
        self.error_message = error_message
        self.checked_at = checked_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "monitor_id": self.monitor_id,
            "monitor_name": self.monitor_name,
            "status_code": self.status_code,
            "response_time_ms": self.response_time_ms,
            "is_success": self.is_success,
            "error_message": self.error_message,
            "checked_at": self.checked_at,
        }


class UptimeReport:
    """An uptime report for a monitor."""

    def __init__(
        self,
        monitor_id: str,
        monitor_name: str,
        period_hours: int,
        total_checks: int,
        successful_checks: int,
        uptime_percentage: float,
        avg_response_time_ms: float,
        p95_response_time_ms: float,
        p99_response_time_ms: float,
    ):
        self.monitor_id = monitor_id
        self.monitor_name = monitor_name
        self.period_hours = period_hours
        self.total_checks = total_checks
        self.successful_checks = successful_checks
        self.uptime_percentage = uptime_percentage
        self.avg_response_time_ms = avg_response_time_ms
        self.p95_response_time_ms = p95_response_time_ms
        self.p99_response_time_ms = p99_response_time_ms

    def to_dict(self) -> dict:
        return {
            "monitor_id": self.monitor_id,
            "monitor_name": self.monitor_name,
            "period_hours": self.period_hours,
            "total_checks": self.total_checks,
            "successful_checks": self.successful_checks,
            "uptime_percentage": self.uptime_percentage,
            "avg_response_time_ms": self.avg_response_time_ms,
            "p95_response_time_ms": self.p95_response_time_ms,
            "p99_response_time_ms": self.p99_response_time_ms,
        }
