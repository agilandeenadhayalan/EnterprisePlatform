"""
Retraining Trigger repository — in-memory pre-seeded trigger data.

Seeds trigger rules and evaluation history. Simulates drift detection,
performance degradation, and scheduled retraining triggers.
"""

import random
import uuid
from typing import Optional

from models import RetrainingTrigger, TriggerEvaluation, TriggerHistory


class TriggerRepository:
    """In-memory trigger data store with pre-seeded sample data."""

    def __init__(self, seed: bool = True):
        self._triggers: dict[str, RetrainingTrigger] = {}
        self._history: list[TriggerHistory] = []
        self._rng = random.Random(42)

        if seed:
            self._seed_data()

    def _seed_data(self):
        """Pre-populate with trigger rules and evaluation history."""
        triggers_config = [
            {
                "id": "trig-001",
                "model_name": "fare_predictor_nn",
                "trigger_type": "drift",
                "condition": "psi > threshold",
                "threshold": 0.2,
                "cooldown_hours": 24,
                "is_active": True,
                "last_fired_at": "2024-01-12T08:00:00Z",
                "created_at": "2024-01-01T00:00:00Z",
            },
            {
                "id": "trig-002",
                "model_name": "demand_predictor_gb",
                "trigger_type": "drift",
                "condition": "ks_stat > threshold",
                "threshold": 0.15,
                "cooldown_hours": 48,
                "is_active": True,
                "last_fired_at": None,
                "created_at": "2024-01-02T00:00:00Z",
            },
            {
                "id": "trig-003",
                "model_name": "fare_predictor_nn",
                "trigger_type": "performance",
                "condition": "rmse > threshold",
                "threshold": 4.0,
                "cooldown_hours": 12,
                "is_active": True,
                "last_fired_at": "2024-01-14T10:00:00Z",
                "created_at": "2024-01-03T00:00:00Z",
            },
            {
                "id": "trig-004",
                "model_name": "eta_predictor_nn",
                "trigger_type": "scheduled",
                "condition": "days_since_training > threshold",
                "threshold": 7.0,
                "cooldown_hours": 168,
                "is_active": False,
                "last_fired_at": "2024-01-08T00:00:00Z",
                "created_at": "2024-01-04T00:00:00Z",
            },
        ]

        for cfg in triggers_config:
            trigger = RetrainingTrigger(**cfg)
            self._triggers[trigger.id] = trigger

        # Seed history
        history_entries = [
            TriggerHistory(
                trigger_id="trig-001",
                model_name="fare_predictor_nn",
                fired_at="2024-01-12T08:00:00Z",
                reason="PSI=0.28 exceeds threshold 0.2: significant feature drift detected",
            ),
            TriggerHistory(
                trigger_id="trig-003",
                model_name="fare_predictor_nn",
                fired_at="2024-01-14T10:00:00Z",
                reason="RMSE=4.52 exceeds threshold 4.0: model performance degraded",
            ),
            TriggerHistory(
                trigger_id="trig-001",
                model_name="fare_predictor_nn",
                fired_at="2024-01-05T12:00:00Z",
                reason="PSI=0.25 exceeds threshold 0.2: significant feature drift detected",
            ),
            TriggerHistory(
                trigger_id="trig-004",
                model_name="eta_predictor_nn",
                fired_at="2024-01-08T00:00:00Z",
                reason="8 days since last training exceeds threshold of 7 days",
            ),
            TriggerHistory(
                trigger_id="trig-002",
                model_name="demand_predictor_gb",
                fired_at="2024-01-06T16:00:00Z",
                reason="KS stat=0.18 exceeds threshold 0.15: distribution drift detected",
            ),
            TriggerHistory(
                trigger_id="trig-003",
                model_name="fare_predictor_nn",
                fired_at="2024-01-10T09:00:00Z",
                reason="RMSE=4.35 exceeds threshold 4.0: model performance degraded",
            ),
        ]
        self._history = history_entries

    # ── Trigger operations ──

    def create_trigger(
        self,
        model_name: str,
        trigger_type: str,
        condition: str,
        threshold: float,
        cooldown_hours: int,
        is_active: bool,
    ) -> RetrainingTrigger:
        """Create a new retraining trigger rule."""
        trig_id = f"trig-{uuid.uuid4().hex[:8]}"
        trigger = RetrainingTrigger(
            id=trig_id,
            model_name=model_name,
            trigger_type=trigger_type,
            condition=condition,
            threshold=threshold,
            cooldown_hours=cooldown_hours,
            is_active=is_active,
            created_at="2024-01-15T10:00:00Z",
        )
        self._triggers[trig_id] = trigger
        return trigger

    def list_triggers(self) -> list[RetrainingTrigger]:
        """Return all trigger rules."""
        return list(self._triggers.values())

    def get_trigger(self, trigger_id: str) -> Optional[RetrainingTrigger]:
        """Return a single trigger by ID."""
        return self._triggers.get(trigger_id)

    def evaluate_all(self) -> list[TriggerEvaluation]:
        """Evaluate all active triggers against simulated current metrics."""
        evaluations = []
        for trigger in self._triggers.values():
            if not trigger.is_active:
                # Inactive triggers are not evaluated
                evaluations.append(TriggerEvaluation(
                    trigger_id=trigger.id,
                    fired=False,
                    reason=f"Trigger {trigger.id} is inactive",
                    metric_value=0.0,
                    threshold=trigger.threshold,
                    evaluated_at="2024-01-15T12:00:00Z",
                ))
                continue

            # Simulate current metric values
            if trigger.trigger_type == "drift":
                # Simulate PSI or KS stat
                metric_value = round(self._rng.uniform(0.05, 0.35), 3)
            elif trigger.trigger_type == "performance":
                # Simulate RMSE
                metric_value = round(self._rng.uniform(2.5, 5.5), 2)
            else:
                # Scheduled — days since training
                metric_value = round(self._rng.uniform(1.0, 14.0), 1)

            fired = metric_value > trigger.threshold

            # Check cooldown
            if fired and trigger.last_fired_at is not None:
                # Simplified cooldown: compare dates
                # In seeded data, last_fired_at is recent enough that some triggers
                # will be in cooldown
                if trigger.last_fired_at >= "2024-01-14T00:00:00Z":
                    # Within last day, check cooldown
                    if trigger.cooldown_hours >= 24:
                        fired = False
                        reason = (
                            f"Metric {metric_value} exceeds threshold {trigger.threshold} "
                            f"but trigger is in cooldown (last fired: {trigger.last_fired_at})"
                        )
                        evaluations.append(TriggerEvaluation(
                            trigger_id=trigger.id,
                            fired=False,
                            reason=reason,
                            metric_value=metric_value,
                            threshold=trigger.threshold,
                            evaluated_at="2024-01-15T12:00:00Z",
                        ))
                        continue

            if fired:
                reason = (
                    f"Metric value {metric_value} exceeds threshold {trigger.threshold}: "
                    f"retraining triggered for {trigger.model_name}"
                )
                trigger.last_fired_at = "2024-01-15T12:00:00Z"
                self._history.append(TriggerHistory(
                    trigger_id=trigger.id,
                    model_name=trigger.model_name,
                    fired_at="2024-01-15T12:00:00Z",
                    reason=reason,
                ))
            else:
                reason = (
                    f"Metric value {metric_value} is within threshold {trigger.threshold}: "
                    f"no action needed"
                )

            evaluations.append(TriggerEvaluation(
                trigger_id=trigger.id,
                fired=fired,
                reason=reason,
                metric_value=metric_value,
                threshold=trigger.threshold,
                evaluated_at="2024-01-15T12:00:00Z",
            ))

        return evaluations

    def fire_trigger(self, trigger_id: str) -> Optional[TriggerHistory]:
        """Manually fire a trigger. Returns None if not found."""
        trigger = self._triggers.get(trigger_id)
        if trigger is None:
            return None
        trigger.last_fired_at = "2024-01-15T12:00:00Z"
        entry = TriggerHistory(
            trigger_id=trigger.id,
            model_name=trigger.model_name,
            fired_at="2024-01-15T12:00:00Z",
            reason=f"Manually fired by user for model {trigger.model_name}",
        )
        self._history.append(entry)
        return entry

    def get_history(self) -> list[TriggerHistory]:
        """Return all trigger firing history."""
        return self._history


# Singleton repository instance
repo = TriggerRepository(seed=True)
