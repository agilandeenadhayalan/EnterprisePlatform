"""
Saga Pattern — Distributed Transaction Coordination
=====================================================

Implements the Saga orchestrator pattern for managing distributed
transactions across microservices. Each saga step has a forward action
and a compensating (rollback) action.

WHY sagas over distributed transactions (2PC):
- 2PC requires locking resources across services (doesn't scale)
- Sagas use eventual consistency — each step commits independently
- If a step fails, compensating actions undo previous steps
- Better availability in distributed systems

Ride Booking Saga:
    reserve_driver --> calculate_price --> charge_payment --> confirm_trip
         |                  |                   |                |
    [compensate]      [compensate]        [compensate]      [compensate]
    release_driver   clear_price_cache   refund_payment    cancel_trip

If charge_payment fails:
    clear_price_cache --> release_driver --> SAGA FAILED
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class SagaStepStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATED = "compensated"


class SagaStatus(str, Enum):
    NOT_STARTED = "not_started"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPENSATING = "compensating"
    FAILED = "failed"


@dataclass
class SagaStep:
    """
    A single step in a saga with forward and compensating actions.

    The forward action does the work. If a later step fails,
    the compensating action undoes this step's work.
    """
    name: str
    action: Callable[[dict[str, Any]], bool]       # Returns True on success
    compensate: Callable[[dict[str, Any]], bool]   # Undo action
    status: SagaStepStatus = SagaStepStatus.PENDING


@dataclass
class SagaLog:
    """Audit log entry for saga execution."""
    step_name: str
    action_type: str  # "forward" or "compensate"
    success: bool
    message: str = ""


class SagaOrchestrator:
    """
    Orchestrates a saga — a sequence of steps with compensating actions.

    The orchestrator:
    1. Executes steps in order
    2. If a step fails, runs compensating actions in reverse order
    3. Maintains an audit log of all actions taken

    This is the ORCHESTRATION pattern (central coordinator).
    Alternative: CHOREOGRAPHY pattern (services react to events).
    """

    def __init__(self, saga_name: str) -> None:
        self.saga_name = saga_name
        self.steps: list[SagaStep] = []
        self.status = SagaStatus.NOT_STARTED
        self.log: list[SagaLog] = []
        self.context: dict[str, Any] = {}

    def add_step(
        self,
        name: str,
        action: Callable[[dict[str, Any]], bool],
        compensate: Callable[[dict[str, Any]], bool],
    ) -> None:
        """Add a step to the saga."""
        self.steps.append(SagaStep(name=name, action=action, compensate=compensate))

    def execute(self, context: dict[str, Any] | None = None) -> bool:
        """
        Execute the saga — run all steps or compensate on failure.

        Returns True if all steps completed successfully.
        """
        self.context = context if context is not None else {}
        self.status = SagaStatus.RUNNING
        completed_steps: list[SagaStep] = []

        for step in self.steps:
            try:
                success = step.action(self.context)
                if success:
                    step.status = SagaStepStatus.COMPLETED
                    completed_steps.append(step)
                    self.log.append(SagaLog(
                        step_name=step.name,
                        action_type="forward",
                        success=True,
                        message=f"Step '{step.name}' completed",
                    ))
                else:
                    step.status = SagaStepStatus.FAILED
                    self.log.append(SagaLog(
                        step_name=step.name,
                        action_type="forward",
                        success=False,
                        message=f"Step '{step.name}' failed",
                    ))
                    self._compensate(completed_steps)
                    return False
            except Exception as e:
                step.status = SagaStepStatus.FAILED
                self.log.append(SagaLog(
                    step_name=step.name,
                    action_type="forward",
                    success=False,
                    message=f"Step '{step.name}' raised: {e}",
                ))
                self._compensate(completed_steps)
                return False

        self.status = SagaStatus.COMPLETED
        return True

    def _compensate(self, completed_steps: list[SagaStep]) -> None:
        """Run compensating actions in reverse order."""
        self.status = SagaStatus.COMPENSATING

        for step in reversed(completed_steps):
            try:
                step.compensate(self.context)
                step.status = SagaStepStatus.COMPENSATED
                self.log.append(SagaLog(
                    step_name=step.name,
                    action_type="compensate",
                    success=True,
                    message=f"Compensated '{step.name}'",
                ))
            except Exception as e:
                self.log.append(SagaLog(
                    step_name=step.name,
                    action_type="compensate",
                    success=False,
                    message=f"Compensation failed for '{step.name}': {e}",
                ))

        self.status = SagaStatus.FAILED


# ── Ride Booking Saga Builder ──


def build_ride_booking_saga(
    fail_at_step: str | None = None,
) -> SagaOrchestrator:
    """
    Build a ride booking saga with configurable failure injection.

    Steps:
    1. reserve_driver — Hold a driver for this ride
    2. calculate_price — Compute fare based on route/surge
    3. charge_payment — Charge the rider's payment method
    4. confirm_trip — Finalize the trip and notify parties

    Args:
        fail_at_step: Name of step to simulate failure at (for testing)
    """
    saga = SagaOrchestrator("ride_booking")

    def reserve_driver(ctx: dict[str, Any]) -> bool:
        if fail_at_step == "reserve_driver":
            return False
        ctx["driver_reserved"] = True
        ctx["driver_id"] = "driver-042"
        return True

    def release_driver(ctx: dict[str, Any]) -> bool:
        ctx["driver_reserved"] = False
        ctx["driver_id"] = None
        return True

    def calculate_price(ctx: dict[str, Any]) -> bool:
        if fail_at_step == "calculate_price":
            return False
        ctx["price_calculated"] = True
        ctx["fare_amount"] = 15.50
        return True

    def clear_price(ctx: dict[str, Any]) -> bool:
        ctx["price_calculated"] = False
        ctx["fare_amount"] = None
        return True

    def charge_payment(ctx: dict[str, Any]) -> bool:
        if fail_at_step == "charge_payment":
            return False
        ctx["payment_charged"] = True
        ctx["charge_id"] = "chg-001"
        return True

    def refund_payment(ctx: dict[str, Any]) -> bool:
        ctx["payment_charged"] = False
        ctx["charge_id"] = None
        ctx["refunded"] = True
        return True

    def confirm_trip(ctx: dict[str, Any]) -> bool:
        if fail_at_step == "confirm_trip":
            return False
        ctx["trip_confirmed"] = True
        return True

    def cancel_trip(ctx: dict[str, Any]) -> bool:
        ctx["trip_confirmed"] = False
        ctx["trip_cancelled"] = True
        return True

    saga.add_step("reserve_driver", reserve_driver, release_driver)
    saga.add_step("calculate_price", calculate_price, clear_price)
    saga.add_step("charge_payment", charge_payment, refund_payment)
    saga.add_step("confirm_trip", confirm_trip, cancel_trip)

    return saga
