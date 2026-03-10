"""
Fleet Simulator repository — in-memory fleet simulation state.

Manages fleet runs, drivers, demand events, and supply/demand analytics.
"""

import random
import uuid
from datetime import datetime
from typing import Any, Optional

from models import FleetRun, SimDriver, DemandEvent


class FleetSimulatorRepository:
    """In-memory fleet simulation storage."""

    def __init__(self):
        self._runs: dict[str, FleetRun] = {}
        self._drivers: dict[str, list[SimDriver]] = {}  # run_id -> drivers
        self._demand: dict[str, list[DemandEvent]] = {}  # run_id -> demand events
        self._pending_requests: dict[str, int] = {}  # run_id -> count

    # ── Runs ──

    def create_run(
        self,
        num_drivers: int = 10,
        config: Optional[dict[str, Any]] = None,
    ) -> FleetRun:
        """Start a fleet simulation run."""
        run_id = str(uuid.uuid4())
        run = FleetRun(
            id=run_id,
            status="created",
            num_drivers=num_drivers,
            config=config,
        )
        self._runs[run_id] = run
        self._drivers[run_id] = []
        self._demand[run_id] = []
        self._pending_requests[run_id] = 0

        # Create drivers
        for _ in range(num_drivers):
            driver = SimDriver(id=str(uuid.uuid4()), run_id=run_id)
            self._drivers[run_id].append(driver)

        return run

    def list_runs(self) -> list[FleetRun]:
        """List all runs."""
        return list(self._runs.values())

    def get_run(self, run_id: str) -> Optional[FleetRun]:
        """Get a run by ID."""
        return self._runs.get(run_id)

    # ── Drivers ──

    def get_drivers(self, run_id: str) -> list[SimDriver]:
        """Get drivers in a run."""
        return self._drivers.get(run_id, [])

    # ── Demand ──

    def inject_demand(
        self,
        run_id: str,
        pickup: Optional[dict] = None,
        dropoff: Optional[dict] = None,
    ) -> Optional[DemandEvent]:
        """Inject a demand event."""
        if run_id not in self._runs:
            return None
        event = DemandEvent(
            id=str(uuid.uuid4()),
            run_id=run_id,
            pickup=pickup,
            dropoff=dropoff,
        )
        self._demand[run_id].append(event)
        self._pending_requests[run_id] = self._pending_requests.get(run_id, 0) + 1
        return event

    # ── Step ──

    def step(self, run_id: str) -> Optional[dict]:
        """Step fleet simulation."""
        run = self._runs.get(run_id)
        if not run:
            return None
        if run.status not in ("created", "running"):
            return None

        run.status = "running"
        run.num_ticks += 1

        drivers = self._drivers.get(run_id, [])
        drivers_moved = 0
        trips_started = 0
        trips_completed = 0

        for driver in drivers:
            # Move driver
            driver.position["lat"] += random.uniform(-0.002, 0.002)
            driver.position["lon"] += random.uniform(-0.002, 0.002)
            drivers_moved += 1

            # State transitions
            if driver.state == "idle" and self._pending_requests.get(run_id, 0) > 0:
                driver.state = "en_route_pickup"
                driver.current_trip_id = str(uuid.uuid4())
                self._pending_requests[run_id] -= 1
                trips_started += 1
            elif driver.state == "en_route_pickup":
                if random.random() < 0.5:
                    driver.state = "on_trip"
            elif driver.state == "on_trip":
                if random.random() < 0.3:
                    driver.state = "idle"
                    driver.current_trip_id = None
                    trips_completed += 1

        return {
            "tick": run.num_ticks,
            "drivers_moved": drivers_moved,
            "trips_started": trips_started,
            "trips_completed": trips_completed,
            "status": run.status,
        }

    # ── Analytics ──

    def get_supply_demand(self, run_id: str) -> Optional[dict]:
        """Get supply/demand analytics."""
        drivers = self._drivers.get(run_id)
        if drivers is None:
            return None
        idle = sum(1 for d in drivers if d.state == "idle")
        active = sum(1 for d in drivers if d.state in ("en_route_pickup", "on_trip"))
        total = len(drivers)
        pending = self._pending_requests.get(run_id, 0)

        return {
            "idle_drivers": idle,
            "active_drivers": active,
            "pending_requests": pending,
            "utilization_rate": round(active / total, 4) if total > 0 else 0.0,
        }


# Singleton repository instance
repo = FleetSimulatorRepository()
