"""
City Simulator repository — in-memory simulation state.

Manages simulation runs, agents, ticks, and metrics.
"""

import random
import uuid
from datetime import datetime
from typing import Any, Optional

from models import SimulationRun, SimAgent, SimulationMetrics


class CitySimulatorRepository:
    """In-memory city simulation storage."""

    def __init__(self):
        self._runs: dict[str, SimulationRun] = {}
        self._agents: dict[str, list[SimAgent]] = {}  # run_id -> agents
        self._metrics: dict[str, SimulationMetrics] = {}  # run_id -> metrics

    # ── Runs ──

    def create_run(
        self,
        simulation_type: str = "city",
        scenario: Optional[dict[str, Any]] = None,
        num_agents: int = 0,
    ) -> SimulationRun:
        """Create a simulation run."""
        run_id = str(uuid.uuid4())
        run = SimulationRun(
            id=run_id,
            simulation_type=simulation_type,
            scenario=scenario,
            status="created",
            num_agents=num_agents,
        )
        self._runs[run_id] = run
        self._agents[run_id] = []
        self._metrics[run_id] = SimulationMetrics()
        return run

    def list_runs(self) -> list[SimulationRun]:
        """List all runs."""
        return list(self._runs.values())

    def get_run(self, run_id: str) -> Optional[SimulationRun]:
        """Get a run by ID."""
        return self._runs.get(run_id)

    def update_run(self, run_id: str, **fields) -> Optional[SimulationRun]:
        """Update run fields."""
        run = self._runs.get(run_id)
        if not run:
            return None
        for key, value in fields.items():
            if value is not None and hasattr(run, key):
                setattr(run, key, value)
        if fields.get("status") in ("completed", "stopped"):
            run.completed_at = datetime.utcnow()
        return run

    # ── Agents ──

    def add_agents(self, run_id: str, agent_type: str, count: int) -> list[SimAgent]:
        """Add agents to a simulation run."""
        if run_id not in self._runs:
            return []
        agents = []
        for _ in range(count):
            agent = SimAgent(
                id=str(uuid.uuid4()),
                run_id=run_id,
                agent_type=agent_type,
            )
            agents.append(agent)
        self._agents[run_id].extend(agents)
        self._runs[run_id].num_agents = len(self._agents[run_id])
        return agents

    def list_agents(self, run_id: str) -> list[SimAgent]:
        """List agents in a run."""
        return self._agents.get(run_id, [])

    # ── Simulation step ──

    def step(self, run_id: str) -> Optional[dict]:
        """Advance simulation by one tick."""
        run = self._runs.get(run_id)
        if not run:
            return None
        if run.status not in ("created", "running"):
            return None

        run.status = "running"
        run.num_ticks += 1

        # Move agents randomly
        agents = self._agents.get(run_id, [])
        agents_moved = 0
        trips_completed = 0
        for agent in agents:
            agent.position["lat"] += random.uniform(-0.001, 0.001)
            agent.position["lon"] += random.uniform(-0.001, 0.001)
            agents_moved += 1
            if random.random() < 0.1:  # 10% chance of completing a trip
                trips_completed += 1

        # Update metrics
        metrics = self._metrics[run_id]
        metrics.total_trips += trips_completed
        if len(agents) > 0:
            metrics.utilization = min(1.0, metrics.total_trips / (len(agents) * max(1, run.num_ticks)))
            drivers = [a for a in agents if a.agent_type == "driver"]
            riders = [a for a in agents if a.agent_type == "rider"]
            if riders:
                metrics.supply_demand_ratio = len(drivers) / len(riders) if riders else 1.0
            metrics.avg_wait_time = random.uniform(2.0, 8.0)
            metrics.avg_trip_time = random.uniform(10.0, 30.0)

        return {
            "tick": run.num_ticks,
            "agents_moved": agents_moved,
            "trips_completed": trips_completed,
            "status": run.status,
        }

    # ── Metrics ──

    def get_metrics(self, run_id: str) -> Optional[SimulationMetrics]:
        """Get simulation metrics."""
        return self._metrics.get(run_id)


# Singleton repository instance
repo = CitySimulatorRepository()
