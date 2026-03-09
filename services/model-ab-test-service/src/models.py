"""
Domain models for the model A/B test service.

Represents A/B tests, variant tracking, and statistical significance results.
"""

from datetime import datetime, timezone
from typing import Optional


class ABVariant:
    """A variant (champion or challenger) in an A/B test."""

    def __init__(
        self,
        name: str,
        model_name: str,
        traffic_pct: float,
        request_count: int = 0,
        total_value: float = 0.0,
    ):
        self.name = name
        self.model_name = model_name
        self.traffic_pct = traffic_pct
        self.request_count = request_count
        self.total_value = total_value
        self._values: list[float] = []

    def record_outcome(self, value: float):
        """Record an outcome value for this variant."""
        self.request_count += 1
        self.total_value += value
        self._values.append(value)

    @property
    def avg_value(self) -> float:
        if self.request_count == 0:
            return 0.0
        return round(self.total_value / self.request_count, 4)

    @property
    def values(self) -> list[float]:
        return self._values

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "model_name": self.model_name,
            "traffic_pct": self.traffic_pct,
            "request_count": self.request_count,
            "total_value": round(self.total_value, 4),
            "avg_value": self.avg_value,
        }


class ABTest:
    """An A/B test comparing a champion model against a challenger."""

    def __init__(
        self,
        id: str,
        name: str,
        champion_model: str,
        challenger_model: str,
        traffic_split: float = 0.5,
        status: str = "active",
        winner: Optional[str] = None,
        created_at: Optional[str] = None,
        concluded_at: Optional[str] = None,
    ):
        self.id = id
        self.name = name
        self.champion_model = champion_model
        self.challenger_model = challenger_model
        self.traffic_split = traffic_split
        self.status = status
        self.winner = winner
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()
        self.concluded_at = concluded_at

        self.champion = ABVariant(
            name="champion",
            model_name=champion_model,
            traffic_pct=round(1.0 - traffic_split, 2),
        )
        self.challenger = ABVariant(
            name="challenger",
            model_name=challenger_model,
            traffic_pct=traffic_split,
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "champion_model": self.champion_model,
            "challenger_model": self.challenger_model,
            "traffic_split": self.traffic_split,
            "status": self.status,
            "winner": self.winner,
            "created_at": self.created_at,
            "concluded_at": self.concluded_at,
            "champion": self.champion.to_dict(),
            "challenger": self.challenger.to_dict(),
        }


class SignificanceResult:
    """Statistical significance test result."""

    def __init__(
        self,
        p_value: float,
        is_significant: bool,
        recommended_action: str,
    ):
        self.p_value = p_value
        self.is_significant = is_significant
        self.recommended_action = recommended_action

    def to_dict(self) -> dict:
        return {
            "p_value": self.p_value,
            "is_significant": self.is_significant,
            "recommended_action": self.recommended_action,
        }
