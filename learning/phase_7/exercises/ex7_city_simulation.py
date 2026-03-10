"""
Exercise 7: City Simulation — Dispatch and Movement
========================================
Implement a simple city simulation with nearest-driver dispatch and
vehicle movement toward destinations.

WHY THIS MATTERS:
A mobility platform is fundamentally a multi-agent system. Dispatch
decides which driver serves which rider, and movement simulation
determines when pickups and dropoffs occur. These two mechanisms
are the heartbeat of any ride-sharing platform.

Understanding dispatch and movement builds intuition for:
  - Spatial algorithms (nearest-neighbor search)
  - State machines (vehicle lifecycle: idle -> pickup -> dropoff)
  - Discrete-time simulation (tick-based movement)
  - Supply/demand matching under constraints

YOUR TASK:
Implement two methods in SimpleCity:

1. dispatch(request) — assign the nearest idle vehicle to the request
   - Find all vehicles with status "idle"
   - Calculate distance from each idle vehicle to request.pickup
   - Assign the closest one (set vehicle.destination = request.pickup,
     vehicle.status = "en_route_pickup", vehicle.current_request = request,
     request.assigned_vehicle_id = vehicle.id)
   - Return the assigned vehicle ID, or None if no idle vehicles

2. step() — advance the simulation by one tick
   - For each vehicle that has a destination:
     a. Calculate distance to destination
     b. If distance <= vehicle.speed: arrive (set position = destination)
        - If status is "en_route_pickup": switch to "en_route_dropoff",
          set destination = current_request.dropoff
        - If status is "en_route_dropoff": complete the trip,
          set status = "idle", destination = None, current_request = None,
          increment self.completed_trips
     c. If distance > speed: move toward destination by speed units
        (dx/dist * speed, dy/dist * speed)

The Vehicle, RideRequest, and SimpleCity scaffold are provided.
"""

import math
from dataclasses import dataclass


@dataclass
class Position:
    """A 2D coordinate."""
    x: float
    y: float

    def distance_to(self, other: "Position") -> float:
        """Euclidean distance to another position."""
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)


@dataclass
class RideRequest:
    """A ride request with pickup and dropoff locations."""
    id: str
    pickup: Position
    dropoff: Position
    assigned_vehicle_id: str = None


class Vehicle:
    """A vehicle that can be dispatched to serve rides."""

    def __init__(self, vehicle_id: str, position: Position, speed: float = 1.0):
        self.id = vehicle_id
        self.position = position
        self.speed = speed
        self.status = "idle"  # "idle", "en_route_pickup", "en_route_dropoff"
        self.destination: Position = None
        self.current_request: RideRequest = None


class SimpleCity:
    """A simple city simulation with vehicles and ride requests."""

    def __init__(self):
        self._vehicles: dict = {}
        self.completed_trips: int = 0

    def add_vehicle(self, vehicle: Vehicle) -> None:
        """Register a vehicle in the city."""
        self._vehicles[vehicle.id] = vehicle

    def get_vehicle(self, vehicle_id: str) -> Vehicle:
        """Get a vehicle by ID."""
        return self._vehicles.get(vehicle_id)

    def dispatch(self, request: RideRequest):
        """Assign the nearest idle vehicle to the request.

        Algorithm:
            1. Find all vehicles with status == "idle"
            2. If none: return None
            3. Find the vehicle closest to request.pickup (Euclidean distance)
            4. Set that vehicle's:
               - destination = request.pickup
               - status = "en_route_pickup"
               - current_request = request
            5. Set request.assigned_vehicle_id = vehicle.id
            6. Return the vehicle's ID

        Returns:
            Vehicle ID of the assigned vehicle, or None if no idle vehicles.
        """
        # YOUR CODE HERE (~12 lines)
        raise NotImplementedError("Implement dispatch")

    def step(self) -> None:
        """Advance all vehicles by one tick.

        For each vehicle with a destination:
            1. dist = position.distance_to(destination)
            2. If dist <= speed:
               - position = Position(destination.x, destination.y)
               - If status == "en_route_pickup":
                   status = "en_route_dropoff"
                   destination = current_request.dropoff
               - If status == "en_route_dropoff":
                   status = "idle"
                   destination = None
                   current_request = None
                   self.completed_trips += 1
            3. If dist > speed:
               - dx = destination.x - position.x
               - dy = destination.y - position.y
               - ratio = speed / dist
               - position = Position(position.x + dx * ratio,
                                     position.y + dy * ratio)
        """
        # YOUR CODE HERE (~20 lines)
        raise NotImplementedError("Implement step")


# ── Verification ──


def test_nearest_dispatch():
    """Nearest idle vehicle is dispatched."""
    city = SimpleCity()
    city.add_vehicle(Vehicle("v1", Position(0, 0), speed=1.0))
    city.add_vehicle(Vehicle("v2", Position(10, 10), speed=1.0))
    req = RideRequest("r1", Position(1, 1), Position(5, 5))
    assigned = city.dispatch(req)
    assert assigned == "v1", f"Expected v1 (nearest), got {assigned}"
    print("[PASS] test_nearest_dispatch")


def test_no_idle():
    """No idle vehicles returns None."""
    city = SimpleCity()
    v = Vehicle("v1", Position(0, 0))
    v.status = "en_route_pickup"
    city.add_vehicle(v)
    result = city.dispatch(RideRequest("r2", Position(1, 1), Position(5, 5)))
    assert result is None, f"Expected None, got {result}"
    print("[PASS] test_no_idle")


def test_movement():
    """Vehicle moves toward destination on step."""
    city = SimpleCity()
    v = Vehicle("v1", Position(0, 0), speed=1.0)
    city.add_vehicle(v)
    city.dispatch(RideRequest("r1", Position(5, 0), Position(10, 0)))
    city.step()
    assert abs(v.position.x - 1.0) < 0.01, f"Expected x~1.0, got {v.position.x}"
    print("[PASS] test_movement")


def test_trip_completion():
    """Vehicle completes full trip lifecycle."""
    city = SimpleCity()
    v = Vehicle("v1", Position(0, 0), speed=100.0)
    city.add_vehicle(v)
    city.dispatch(RideRequest("r1", Position(1, 0), Position(2, 0)))
    city.step()  # arrive at pickup
    city.step()  # arrive at dropoff
    assert v.status == "idle", f"Expected idle, got {v.status}"
    assert city.completed_trips == 1, f"Expected 1, got {city.completed_trips}"
    print("[PASS] test_trip_completion")


def test_multiple_concurrent():
    """Multiple vehicles serve concurrent rides."""
    city = SimpleCity()
    city.add_vehicle(Vehicle("v1", Position(0, 0), speed=50.0))
    city.add_vehicle(Vehicle("v2", Position(10, 10), speed=50.0))
    city.dispatch(RideRequest("r1", Position(0, 1), Position(0, 5)))
    city.dispatch(RideRequest("r2", Position(10, 11), Position(10, 15)))
    city.step()  # both arrive at pickups
    city.step()  # both arrive at dropoffs
    assert city.completed_trips == 2, f"Expected 2, got {city.completed_trips}"
    print("[PASS] test_multiple_concurrent")


if __name__ == "__main__":
    test_nearest_dispatch()
    test_no_idle()
    test_movement()
    test_trip_completion()
    test_multiple_concurrent()
    print("\nAll checks passed!")
