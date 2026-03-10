"""
Agent-based modeling — drivers and riders as autonomous agents.

WHY THIS MATTERS:
A mobility platform is fundamentally a multi-agent system: thousands
of drivers and riders independently making decisions that collectively
determine system behavior. Agent-based modeling lets us test dispatch
algorithms, pricing strategies, and fleet sizing in simulation before
deploying to production.

Key concepts:
  - Agent abstraction: each entity has state and a step() method
  - State machines: agents transition through well-defined states
  - Spatial simulation: agents move through a coordinate grid
  - Ride lifecycle: request -> assignment -> pickup -> dropoff -> complete
"""

import math
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod


@dataclass
class Position:
    """A 2D coordinate in the simulation grid.

    Represents a location using (x, y) floating-point coordinates.
    Provides Euclidean distance calculation for ETA estimation.
    """

    x: float
    y: float

    def distance_to(self, other: "Position") -> float:
        """Calculate Euclidean distance to another position."""
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)


class AgentState(Enum):
    """Possible states for agents in the simulation.

    Defines the lifecycle of both drivers and riders:
    - IDLE: not engaged in any ride
    - REQUESTING: rider has submitted a ride request
    - WAITING: rider is waiting for driver assignment/arrival
    - EN_ROUTE_PICKUP: driver heading to pick up rider
    - EN_ROUTE_DROPOFF: driver carrying rider to destination
    - COMPLETED: ride finished
    """

    IDLE = "idle"
    REQUESTING = "requesting"
    WAITING = "waiting"
    EN_ROUTE_PICKUP = "en_route_pickup"
    EN_ROUTE_DROPOFF = "en_route_dropoff"
    COMPLETED = "completed"


class Agent(ABC):
    """Base class for all agents in the simulation.

    Each agent has an ID, position, and state, and must implement
    a step() method called on every simulation tick.
    """

    def __init__(self, agent_id: str, position: Position):
        self.id = agent_id
        self.position = position
        self.state = AgentState.IDLE

    @abstractmethod
    def step(self, tick: int) -> None:
        """Advance agent by one simulation tick."""
        pass


class DriverAgent(Agent):
    """A driver agent that moves through the city and serves rides.

    Drivers transition through states: IDLE -> EN_ROUTE_PICKUP ->
    EN_ROUTE_DROPOFF -> IDLE. On each tick, the driver moves toward
    the current destination at a fixed speed.
    """

    def __init__(self, agent_id: str, position: Position, speed: float = 1.0):
        """Initialize a driver agent.

        Args:
            agent_id: unique identifier
            position: starting position
            speed: distance units moved per tick
        """
        super().__init__(agent_id, position)
        self.speed = speed
        self._pickup: Position = None
        self._dropoff: Position = None
        self._destination: Position = None

    def accept_ride(self, pickup: Position, dropoff: Position) -> None:
        """Accept a ride request and head to pickup location.

        Transitions state to EN_ROUTE_PICKUP and sets the first
        destination to the pickup point.
        """
        self._pickup = pickup
        self._dropoff = dropoff
        self._destination = pickup
        self.state = AgentState.EN_ROUTE_PICKUP

    def step(self, tick: int) -> None:
        """Move toward the current destination by one tick's worth of speed.

        When reaching the pickup, transitions to EN_ROUTE_DROPOFF.
        When reaching the dropoff, transitions to IDLE (completed ride).
        """
        if self._destination is None:
            return

        dist = self.position.distance_to(self._destination)

        if dist <= self.speed:
            # Arrived at destination
            self.position = Position(self._destination.x, self._destination.y)

            if self.state == AgentState.EN_ROUTE_PICKUP:
                # Picked up rider, head to dropoff
                self._destination = self._dropoff
                self.state = AgentState.EN_ROUTE_DROPOFF
            elif self.state == AgentState.EN_ROUTE_DROPOFF:
                # Completed the ride
                self._destination = None
                self._pickup = None
                self._dropoff = None
                self.state = AgentState.IDLE
        else:
            # Move toward destination
            dx = self._destination.x - self.position.x
            dy = self._destination.y - self.position.y
            ratio = self.speed / dist
            self.position = Position(
                self.position.x + dx * ratio,
                self.position.y + dy * ratio,
            )

    def is_available(self) -> bool:
        """Check if the driver is idle and can accept rides."""
        return self.state == AgentState.IDLE

    def get_eta(self, target: Position) -> float:
        """Estimate time to reach a target position.

        ETA = distance / speed. Returns ticks (simulation time units).
        """
        if self.speed == 0:
            return float('inf')
        return self.position.distance_to(target) / self.speed


class RiderAgent(Agent):
    """A rider agent that requests rides and waits for drivers.

    Riders have limited patience: if not matched within patience_ticks,
    they cancel the request.
    """

    def __init__(self, agent_id: str, position: Position, patience_ticks: int = 10):
        """Initialize a rider agent.

        Args:
            agent_id: unique identifier
            position: current position (pickup location)
            patience_ticks: how many ticks the rider will wait before cancelling
        """
        super().__init__(agent_id, position)
        self.patience_ticks = patience_ticks
        self._remaining_patience = patience_ticks
        self._dropoff: Position = None

    def request_ride(self, dropoff: Position) -> "RideRequest":
        """Submit a ride request.

        Transitions to WAITING state and returns a RideRequest object.
        """
        self._dropoff = dropoff
        self.state = AgentState.WAITING
        self._remaining_patience = self.patience_ticks
        return RideRequest(
            id=f"req_{self.id}",
            rider_id=self.id,
            pickup=Position(self.position.x, self.position.y),
            dropoff=dropoff,
        )

    def step(self, tick: int) -> None:
        """Decrement patience if waiting. Cancel if expired."""
        if self.state == AgentState.WAITING:
            self._remaining_patience -= 1
            if self._remaining_patience <= 0:
                self.state = AgentState.IDLE  # Cancelled

    def is_waiting(self) -> bool:
        """Check if the rider is currently waiting for a ride."""
        return self.state == AgentState.WAITING

    def is_completed(self) -> bool:
        """Check if the rider's ride has been completed."""
        return self.state == AgentState.COMPLETED


@dataclass
class RideRequest:
    """A ride request from a rider to the dispatch system.

    Tracks the lifecycle of a single ride from request through
    assignment, in-progress, to completion or cancellation.
    """

    id: str
    rider_id: str
    pickup: Position
    dropoff: Position
    created_at_tick: int = 0
    assigned_driver_id: str = None
    status: str = "pending"  # "pending", "assigned", "in_progress", "completed", "cancelled"
