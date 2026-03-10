"""
Discrete-event simulation engine — driving the city simulation forward.

WHY THIS MATTERS:
A simulation engine is the heartbeat of any agent-based model. It
manages time progression, event scheduling, and agent coordination.
Without a well-designed engine, simulations become tangled messes
of ad-hoc timing and order-dependent bugs.

Key concepts:
  - Tick-based time: discrete time steps (vs continuous simulation)
  - Event queue: schedule future events (ride requests, traffic changes)
  - Agent lifecycle: call each agent's step() on every tick
  - Metrics collection: capture per-tick system state for analysis
"""

from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class SimulationConfig:
    """Configuration for a simulation run.

    Defines the simulation grid, agent counts, time resolution,
    and demand parameters.
    """

    grid_size: int = 20               # NxN grid
    num_drivers: int = 10
    num_riders: int = 20
    tick_duration: float = 1.0        # seconds per tick
    demand_rate: float = 0.5          # ride requests per tick


class SimulationClock:
    """Manages simulation time as discrete ticks.

    Each tick represents a fixed duration of simulated time.
    The clock tracks the current tick and converts to elapsed seconds.
    """

    def __init__(self, tick_duration_seconds: float = 1.0):
        """Initialize the clock.

        Args:
            tick_duration_seconds: how many simulated seconds per tick
        """
        self.current_tick: int = 0
        self.tick_duration_seconds = tick_duration_seconds

    def advance(self) -> int:
        """Advance the clock by one tick. Returns the new tick number."""
        self.current_tick += 1
        return self.current_tick

    def elapsed_seconds(self) -> float:
        """Return total elapsed simulated time in seconds."""
        return self.current_tick * self.tick_duration_seconds


@dataclass
class Event:
    """A scheduled event in the simulation.

    Events represent things that happen at specific ticks:
    ride requests, traffic pattern changes, surge pricing triggers, etc.
    """

    tick: int
    event_type: str
    data: dict = field(default_factory=dict)
    source_agent_id: str = None


class EventQueue:
    """Priority queue for simulation events, organized by tick.

    Events are grouped by their scheduled tick. On each tick, the
    engine retrieves and processes all events for that tick.
    """

    def __init__(self):
        self._events: dict = defaultdict(list)

    def schedule(self, event: Event) -> None:
        """Schedule an event for a future tick."""
        self._events[event.tick].append(event)

    def get_events(self, tick: int) -> list:
        """Get all events scheduled for the given tick.

        Returns and removes events for this tick.
        """
        events = self._events.pop(tick, [])
        return events

    def is_empty(self) -> bool:
        """Check if there are any remaining scheduled events."""
        return len(self._events) == 0

    def peek(self) -> Event:
        """Look at the next event without removing it.

        Returns the earliest event, or None if queue is empty.
        """
        if self.is_empty():
            return None
        min_tick = min(self._events.keys())
        return self._events[min_tick][0] if self._events[min_tick] else None


class SimulationEngine:
    """Main simulation engine that coordinates agents, events, and time.

    On each step:
    1. Advance the clock
    2. Process events for this tick
    3. Call each agent's step() method
    4. Collect metrics
    """

    def __init__(self, config: SimulationConfig = None):
        """Initialize the simulation engine.

        Args:
            config: simulation configuration (defaults to SimulationConfig())
        """
        self._config = config or SimulationConfig()
        self._clock = SimulationClock(self._config.tick_duration)
        self._agents: list = []
        self._event_queue = EventQueue()
        self._metrics: list = []
        self._event_log: list = []

    def add_agent(self, agent) -> None:
        """Register an agent with the simulation."""
        self._agents.append(agent)

    def step(self) -> dict:
        """Advance the simulation by one tick.

        Returns a snapshot of the current state after the step.
        """
        tick = self._clock.advance()

        # Process events for this tick
        events = self._event_queue.get_events(tick)
        self._event_log.extend(events)

        # Step all agents
        for agent in self._agents:
            agent.step(tick)

        # Collect tick metrics
        state = self.get_state()
        self._metrics.append({"tick": tick, **state})

        return state

    def run(self, num_ticks: int) -> list:
        """Run the simulation for N ticks.

        Returns list of state snapshots, one per tick.
        """
        results = []
        for _ in range(num_ticks):
            state = self.step()
            results.append(state)
        return results

    def get_state(self) -> dict:
        """Get the current simulation state.

        Returns dict with tick, agent count, and agent states.
        """
        from .agent_model import AgentState

        agent_states = defaultdict(int)
        for agent in self._agents:
            agent_states[agent.state.value] += 1

        return {
            "tick": self._clock.current_tick,
            "num_agents": len(self._agents),
            "agent_states": dict(agent_states),
            "elapsed_seconds": self._clock.elapsed_seconds(),
        }

    @property
    def clock(self) -> SimulationClock:
        """Access the simulation clock."""
        return self._clock

    @property
    def event_queue(self) -> EventQueue:
        """Access the event queue."""
        return self._event_queue
