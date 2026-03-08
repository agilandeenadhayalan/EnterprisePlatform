"""
Demo: Domain-Driven Design
============================

Run: python -m learning.phase_2.src.m07_domain_driven_design.demo
"""

from .bounded_contexts import (
    UserIdentity,
    UserRole,
    Rider,
    Customer,
    Driver,
    Vehicle,
    ContextMapper,
    DriverStatus,
)
from .aggregates import (
    TripAggregate,
    TripStatus,
    Location,
    FareBreakdown,
    InvalidTransitionError,
)


def demo_bounded_contexts() -> None:
    """Show how the same person is modeled differently in each context."""
    print("\n+------------------------------------------+")
    print("|   Demo: Bounded Contexts                 |")
    print("+------------------------------------------+\n")

    # One real-world person, four different models
    user = UserIdentity(
        user_id="user-001",
        email="alice@example.com",
        phone="+1234567890",
        roles=(UserRole.RIDER, UserRole.DRIVER),
        is_verified=True,
    )

    print(f"  Identity Context  : UserIdentity(id={user.user_id}, roles={[r.value for r in user.roles]})")

    # Map to Ride context
    rider = ContextMapper.identity_to_rider(user)
    print(f"  Ride Context      : Rider(id={rider.rider_id}, name='{rider.display_name}', rating={rider.rating})")

    # Map to Payment context
    customer = ContextMapper.identity_to_customer(user)
    print(f"  Payment Context   : Customer(id={customer.customer_id}, payment={customer.default_payment.value})")

    # Map to Driver context
    vehicle = Vehicle(
        vehicle_id="veh-001",
        vehicle_type="standard",
        license_plate="ABC-1234",
    )
    driver = ContextMapper.identity_to_driver(user, vehicle)
    print(f"  Driver Context    : Driver(id={driver.driver_id}, vehicle='{driver.vehicle.vehicle_type}')")

    print("\n  KEY INSIGHT: Same person (user-001), but each context only")
    print("  knows what it needs. The Identity context doesn't know about")
    print("  vehicles, and the Payment context doesn't know about routes.")


def demo_context_mapping() -> None:
    """Show how contexts communicate through mapping."""
    print("\n+------------------------------------------+")
    print("|   Demo: Context Mapping                  |")
    print("+------------------------------------------+\n")

    # Scenario: User wants to book a ride
    user = UserIdentity(
        user_id="user-002",
        email="bob@example.com",
        phone="+1987654321",
        roles=(UserRole.RIDER,),
        is_verified=True,
    )

    print("  Scenario: Bob books a ride")
    print(f"  1. Auth service validates: {user.email} (verified={user.is_verified})")

    rider = ContextMapper.identity_to_rider(user)
    print(f"  2. Ride service creates Rider: {rider.rider_id}")

    customer_id = ContextMapper.rider_to_customer_id(rider)
    print(f"  3. Payment service looks up Customer: {customer_id}")

    # Show that a non-driver can't be mapped to Driver context
    print("\n  Attempting to map Bob (RIDER only) to Driver context...")
    try:
        vehicle = Vehicle("v1", "standard", "XYZ-000")
        ContextMapper.identity_to_driver(user, vehicle)
    except ValueError as e:
        print(f"  [BLOCKED] {e}")


def demo_aggregate_lifecycle() -> None:
    """Walk through a complete trip lifecycle using the aggregate."""
    print("\n+------------------------------------------+")
    print("|   Demo: Trip Aggregate Lifecycle          |")
    print("+------------------------------------------+\n")

    # NYC coordinates
    pickup = Location(lat=40.7484, lon=-73.9857, address="Empire State Building")
    dropoff = Location(lat=40.7580, lon=-73.9855, address="Times Square")

    trip = TripAggregate(
        trip_id="trip-001",
        rider_id="user-001",
        pickup=pickup,
        dropoff=dropoff,
    )

    states = []

    def log_state(action: str) -> None:
        states.append(trip.status.value)
        print(f"  [{trip.status.value:>16}] {action}")

    log_state("Trip requested by rider")

    # Assign driver
    trip.assign_driver("driver-042")
    log_state(f"Driver {trip.driver_id} assigned")

    # Start trip
    trip.start_trip()
    log_state("Trip started (rider picked up)")

    # Add a waypoint
    midpoint = Location(lat=40.7527, lon=-73.9772, address="Grand Central")
    trip.add_waypoint(midpoint)
    log_state(f"Waypoint added ({len(trip.waypoints)} total)")

    # Complete trip
    fare = FareBreakdown(
        base_fare=2.50,
        distance_charge=5.00,
        time_charge=3.00,
        surge_multiplier=1.2,
    )
    trip.complete_trip(fare)
    log_state(f"Trip completed, fare=${fare.total:.2f}")

    print(f"\n  State transitions: {' -> '.join(states)}")
    print(f"  Waypoints recorded: {len(trip.waypoints)}")


def demo_invariant_enforcement() -> None:
    """Show how the aggregate prevents invalid operations."""
    print("\n+------------------------------------------+")
    print("|   Demo: Invariant Enforcement             |")
    print("+------------------------------------------+\n")

    pickup = Location(lat=40.7484, lon=-73.9857)
    dropoff = Location(lat=40.7580, lon=-73.9855)

    # Invariant 1: Can't complete without starting
    print("  Invariant 1: Can't complete without starting")
    trip = TripAggregate(trip_id="inv-1", rider_id="r1", pickup=pickup, dropoff=dropoff)
    try:
        fare = FareBreakdown(base_fare=2.50, distance_charge=5.00, time_charge=3.00)
        trip.complete_trip(fare)
    except InvalidTransitionError as e:
        print(f"  [BLOCKED] {e}\n")

    # Invariant 2: Can't cancel after completion
    print("  Invariant 2: Can't cancel after completion")
    trip2 = TripAggregate(trip_id="inv-2", rider_id="r1", pickup=pickup, dropoff=dropoff)
    trip2.assign_driver("d1")
    trip2.start_trip()
    trip2.complete_trip(FareBreakdown(base_fare=2.50, distance_charge=5.00, time_charge=3.00))
    try:
        trip2.cancel_trip("changed my mind")
    except InvalidTransitionError as e:
        print(f"  [BLOCKED] {e}\n")

    # Invariant 3: Can't start without a driver
    print("  Invariant 3: Can't start without assigning a driver")
    trip3 = TripAggregate(trip_id="inv-3", rider_id="r1", pickup=pickup, dropoff=dropoff)
    try:
        trip3.start_trip()  # No driver assigned
    except InvalidTransitionError as e:
        print(f"  [BLOCKED] {e}\n")

    # Invariant 4: Must have pickup and dropoff
    print("  Invariant 4: Must have pickup and dropoff")
    try:
        TripAggregate(trip_id="inv-4", rider_id="r1", pickup=pickup, dropoff=None)
    except ValueError as e:
        print(f"  [BLOCKED] {e}")


def main() -> None:
    print("=" * 50)
    print("  Module 07: Domain-Driven Design")
    print("=" * 50)

    demo_bounded_contexts()
    demo_context_mapping()
    demo_aggregate_lifecycle()
    demo_invariant_enforcement()

    print("\n[DONE] Module 07 demos complete!\n")


if __name__ == "__main__":
    main()
