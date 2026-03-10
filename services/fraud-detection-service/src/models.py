"""
Domain models for the Fraud Detection service.
"""


class FraudAlert:
    """A fraud alert record."""

    def __init__(
        self,
        id: str,
        transaction_id: str,
        user_id: str,
        risk_score: float,
        alert_type: str,
        status: str,
        details: dict,
        created_at: str = "2026-03-01T00:00:00Z",
    ):
        self.id = id
        self.transaction_id = transaction_id
        self.user_id = user_id
        self.risk_score = risk_score
        self.alert_type = alert_type
        self.status = status
        self.details = details
        self.created_at = created_at
        self.resolved_at: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "transaction_id": self.transaction_id,
            "user_id": self.user_id,
            "risk_score": self.risk_score,
            "alert_type": self.alert_type,
            "status": self.status,
            "details": self.details,
            "created_at": self.created_at,
        }


class FraudRule:
    """A fraud detection rule."""

    def __init__(
        self,
        id: str,
        name: str,
        rule_type: str,
        threshold: float,
        is_active: bool,
        config: dict,
        created_at: str = "2026-03-01T00:00:00Z",
    ):
        self.id = id
        self.name = name
        self.rule_type = rule_type
        self.threshold = threshold
        self.is_active = is_active
        self.config = config
        self.created_at = created_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "rule_type": self.rule_type,
            "threshold": self.threshold,
            "is_active": self.is_active,
            "config": self.config,
            "created_at": self.created_at,
        }


class TransactionScore:
    """A scored transaction result."""

    def __init__(
        self,
        transaction_id: str,
        scores: dict,
        ensemble_score: float,
        flagged: bool,
    ):
        self.transaction_id = transaction_id
        self.scores = scores
        self.ensemble_score = ensemble_score
        self.flagged = flagged

    def to_dict(self) -> dict:
        return {
            "transaction_id": self.transaction_id,
            "scores": self.scores,
            "ensemble_score": self.ensemble_score,
            "flagged": self.flagged,
        }
