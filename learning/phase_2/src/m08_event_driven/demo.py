"""
Demo: Event-Driven Architecture
=================================

Run: python -m learning.phase_2.src.m08_event_driven.demo
"""

from .event_bus import EventBus, DomainEvent
from .saga import build_ride_booking_saga, SagaStatus
from .event_sourcing import EventSourcedTrip, TripEventType


def demo_event_bus() -> None:
    """Show publish/subscribe and event replay."""
    print("\n+------------------------------------------+")
    print("|   Demo: Event Bus (Pub/Sub)              |")
    print("+------------------------------------------+\n")

    bus = EventBus()
    received: list[str] = []

    # Subscribe handlers
    def notification_handler(event: DomainEvent) -> None:
        received.append(f"NOTIFY: {event.event_type} for {event.aggregate_id}")

    def analytics_handler(event: DomainEvent) -> None:
        received.append(f"ANALYTICS: {event.event_type} recorded")

    def failing_handler(event: DomainEvent) -> None:
        raise RuntimeError("Notification service is down!")

    bus.subscribe("TripRequested", notification_handler)
    bus.subscribe("TripRequested", analytics_handler)
    bus.subscribe("TripCompleted", notification_handler)
    bus.subscribe("TripRequested", failing_handler)  # This will fail

    # Publish events
    print("  Publishing TripRequested event...")
    errors = bus.publish(DomainEvent(
        event_type="TripRequested",
        aggregate_id="trip-001",
        data={"rider_id": "rider-1", "pickup": "Empire State Building"},
    ))

    for msg in received:
        print(f"    {msg}")
    if errors:
        print(f"    [ERROR] {errors[0]}")
    print(f"\n  Dead letter queue: {len(bus.dead_letter_queue)} events")

    print("\n  Publishing TripCompleted event...")
    received.clear()
    bus.publish(DomainEvent(
        event_type="TripCompleted",
        aggregate_id="trip-001",
        data={"fare": 15.50},
    ))
    for msg in received:
        print(f"    {msg}")

    # Replay
    print(f"\n  Event store contains {len(bus.event_store)} events")
    replayed = bus.replay(aggregate_id="trip-001")
    print(f"  Replayed {len(replayed)} events for trip-001")


def demo_saga_success() -> None:
    """Show a successful saga execution."""
    print("\n+------------------------------------------+")
    print("|   Demo: Saga — Successful Booking        |")
    print("+------------------------------------------+\n")

    saga = build_ride_booking_saga()
    context = {"rider_id": "rider-1", "pickup": "Times Square"}

    success = saga.execute(context)

    print(f"  Saga result: {'SUCCESS' if success else 'FAILED'}")
    print(f"  Status: {saga.status.value}")
    print(f"\n  Execution log:")
    for entry in saga.log:
        symbol = "[OK]" if entry.success else "[FAIL]"
        print(f"    {symbol} [{entry.action_type:>10}] {entry.message}")

    print(f"\n  Context after saga:")
    for key, value in saga.context.items():
        if key not in ("rider_id", "pickup"):
            print(f"    {key}: {value}")


def demo_saga_failure() -> None:
    """Show saga compensation when a step fails."""
    print("\n+------------------------------------------+")
    print("|   Demo: Saga — Payment Failure + Rollback|")
    print("+------------------------------------------+\n")

    saga = build_ride_booking_saga(fail_at_step="charge_payment")
    context = {"rider_id": "rider-1", "pickup": "Times Square"}

    success = saga.execute(context)

    print(f"  Saga result: {'SUCCESS' if success else 'FAILED'}")
    print(f"  Status: {saga.status.value}")
    print(f"\n  Execution log (notice compensating actions):")
    for entry in saga.log:
        symbol = "[OK]" if entry.success else "[FAIL]"
        marker = " <-- ROLLBACK" if entry.action_type == "compensate" else ""
        print(f"    {symbol} [{entry.action_type:>10}] {entry.message}{marker}")

    print(f"\n  Context after compensation:")
    print(f"    driver_reserved: {context.get('driver_reserved')}")
    print(f"    price_calculated: {context.get('price_calculated')}")
    print(f"    payment_charged: {context.get('payment_charged')}")


def demo_event_sourcing() -> None:
    """Show event sourcing with state replay."""
    print("\n+------------------------------------------+")
    print("|   Demo: Event Sourcing                   |")
    print("+------------------------------------------+\n")

    # Build up state through events
    trip = EventSourcedTrip()
    trip.request_trip("trip-001", "rider-1", 40.7484, -73.9857, 40.7580, -73.9855)
    trip.assign_driver("driver-42")
    trip.start_trip()
    trip.add_waypoint(40.7527, -73.9772)
    trip.complete_trip(15.50)

    print("  Event history:")
    for i, event in enumerate(trip.events, 1):
        print(f"    {i}. {event.event_type.value} (v{i})")

    print(f"\n  Current state (derived from {len(trip.events)} events):")
    s = trip.state
    print(f"    trip_id: {s.trip_id}")
    print(f"    status: {s.status.value}")
    print(f"    driver: {s.driver_id}")
    print(f"    fare: ${s.fare_amount:.2f}")
    print(f"    waypoints: {len(s.waypoints)}")
    print(f"    version: {s.version}")

    # Rebuild from events (the core value of event sourcing)
    print("\n  Rebuilding state from events...")
    rebuilt = EventSourcedTrip.from_events(trip.events)
    print(f"    Rebuilt status: {rebuilt.state.status.value}")
    print(f"    Rebuilt fare: ${rebuilt.state.fare_amount:.2f}")
    print(f"    States match: {rebuilt.state.status == trip.state.status}")

    # Time travel: replay only first 3 events
    print("\n  Time travel: state after 3 events (before completion)...")
    partial = EventSourcedTrip.from_events(trip.events[:3])
    print(f"    Status at v3: {partial.state.status.value}")
    print(f"    Driver at v3: {partial.state.driver_id}")


def main() -> None:
    print("=" * 50)
    print("  Module 08: Event-Driven Architecture")
    print("=" * 50)

    demo_event_bus()
    demo_saga_success()
    demo_saga_failure()
    demo_event_sourcing()

    print("\n[DONE] Module 08 demos complete!\n")


if __name__ == "__main__":
    main()
