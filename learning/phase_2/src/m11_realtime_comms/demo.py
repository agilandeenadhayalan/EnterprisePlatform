"""
Demo: Real-Time Communication
================================

Run: python -m learning.phase_2.src.m11_realtime_comms.demo
"""

from .pubsub import PubSubSystem, Message
from .backpressure import (
    BackpressureStrategy,
    simulate_backpressure,
)
from .presence import PresenceTracker, PresenceState


def demo_pubsub() -> None:
    """Show topic-based pub/sub with wildcards."""
    print("\n+------------------------------------------+")
    print("|   Demo: Pub/Sub with Topic Routing       |")
    print("+------------------------------------------+\n")

    ps = PubSubSystem()
    received: dict[str, list[str]] = {"rider": [], "analytics": [], "map": []}

    # Rider subscribes to their specific trip
    ps.subscribe(
        "trip.123.*",
        "rider-app",
        lambda m: received["rider"].append(f"{m.topic}: {m.payload}"),
    )

    # Analytics subscribes to ALL trip events
    ps.subscribe(
        "trip.#",
        "analytics",
        lambda m: received["analytics"].append(f"{m.topic}"),
    )

    # Map subscribes to ALL location updates
    ps.subscribe(
        "trip.*.location",
        "map-service",
        lambda m: received["map"].append(f"loc({m.payload.get('lat', 0):.4f}, {m.payload.get('lon', 0):.4f})"),
    )

    # Publish events
    ps.publish("trip.123.location", {"lat": 40.7484, "lon": -73.9857, "speed": 25})
    ps.publish("trip.123.status", {"status": "in_progress"})
    ps.publish("trip.456.location", {"lat": 40.7580, "lon": -73.9855, "speed": 30})

    print("  Topic subscriptions:")
    print("    rider-app   -> trip.123.*       (my trip only)")
    print("    analytics   -> trip.#           (all trips)")
    print("    map-service -> trip.*.location  (all locations)")

    print(f"\n  After 3 published messages:")
    print(f"    Rider received:     {len(received['rider'])} messages")
    for msg in received["rider"]:
        print(f"      {msg}")
    print(f"    Analytics received: {len(received['analytics'])} messages")
    print(f"    Map received:       {len(received['map'])} messages")

    # Replay
    history = ps.replay(topic_pattern="trip.123.*")
    print(f"\n  Replay trip.123.*: {len(history)} messages in history")


def demo_backpressure() -> None:
    """Compare backpressure strategies."""
    print("\n+------------------------------------------+")
    print("|   Demo: Backpressure Strategies          |")
    print("+------------------------------------------+\n")

    print("  Scenario: Producer=100 msg/tick, Consumer=40 msg/tick, 20 ticks\n")
    print(f"  {'Strategy':>10} | {'Produced':>10} | {'Consumed':>10} | "
          f"{'Dropped':>8} | {'MaxBuf':>8} | {'Delivery%':>10}")
    print(f"  {'--------':>10} | {'--------':>10} | {'--------':>10} | "
          f"{'-------':>8} | {'------':>8} | {'---------':>10}")

    for strategy in BackpressureStrategy:
        stats = simulate_backpressure(
            strategy=strategy,
            produce_rate=100,
            consume_rate=40,
            ticks=20,
            max_buffer_size=200,
        )
        print(f"  {stats.strategy.value:>10} | {stats.produced:>10} | "
              f"{stats.consumed:>10} | {stats.dropped:>8} | "
              f"{stats.max_buffer_size:>8} | {stats.delivery_rate:>9.1f}%")

    print("\n  Key trade-offs:")
    print("    DROP:     Fast, but loses data (OK for GPS updates)")
    print("    BUFFER:   Keeps all data, but risks memory overflow")
    print("    THROTTLE: Safe and complete, but adds latency")


def demo_presence() -> None:
    """Show presence tracking with heartbeats and timeouts."""
    print("\n+------------------------------------------+")
    print("|   Demo: Presence Tracking                |")
    print("+------------------------------------------+\n")

    tracker = PresenceTracker(away_timeout=30.0, offline_timeout=60.0)

    # Simulate time using explicit timestamps
    base_time = 1000.0

    # Drivers send heartbeats at different times
    tracker.heartbeat("driver-1", {"zone": "midtown"}, timestamp=base_time)
    tracker.heartbeat("driver-2", {"zone": "downtown"}, timestamp=base_time)
    tracker.heartbeat("driver-3", {"zone": "uptown"}, timestamp=base_time)
    tracker.heartbeat("driver-4", {"zone": "brooklyn"}, timestamp=base_time - 45)  # 45s ago
    tracker.heartbeat("driver-5", {"zone": "queens"}, timestamp=base_time - 90)    # 90s ago

    # Check presence at base_time
    print("  Driver presence at T=0:")
    for uid in ["driver-1", "driver-2", "driver-3", "driver-4", "driver-5"]:
        p = tracker.get_presence(uid, now=base_time)
        elapsed = p.seconds_since_heartbeat(base_time)
        print(f"    {uid}: {p.state.value:>8} (heartbeat {elapsed:.0f}s ago, zone={p.metadata.get('zone', '?')})")

    counts = tracker.count_by_state(now=base_time)
    print(f"\n  Summary: {counts[PresenceState.ONLINE]} online, "
          f"{counts[PresenceState.AWAY]} away, "
          f"{counts[PresenceState.OFFLINE]} offline")

    # Time passes — check again at T+40s
    check_time = base_time + 40
    print(f"\n  After 40 seconds (no new heartbeats):")
    for uid in ["driver-1", "driver-2", "driver-3"]:
        p = tracker.get_presence(uid, now=check_time)
        print(f"    {uid}: {p.state.value:>8}")

    counts2 = tracker.count_by_state(now=check_time)
    print(f"\n  Summary: {counts2[PresenceState.ONLINE]} online, "
          f"{counts2[PresenceState.AWAY]} away, "
          f"{counts2[PresenceState.OFFLINE]} offline")


def main() -> None:
    print("=" * 50)
    print("  Module 11: Real-Time Communication")
    print("=" * 50)

    demo_pubsub()
    demo_backpressure()
    demo_presence()

    print("\n[DONE] Module 11 demos complete!\n")


if __name__ == "__main__":
    main()
