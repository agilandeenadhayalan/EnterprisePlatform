"""
Demo: Dispatch Algorithms
===========================

Run: python -m learning.phase_2.src.m09_dispatch_algorithms.demo
"""

from .nearest_driver import (
    DriverLocation,
    RideRequest,
    find_nearest_driver,
    find_k_nearest_drivers,
    haversine_distance,
)
from .scoring import score_drivers, ScoringWeights
from .hungarian import hungarian_match, greedy_match


# ── Sample Data: NYC area ──

DRIVERS = [
    DriverLocation("d1", 40.7484, -73.9857, rating=4.9, acceptance_rate=0.95, idle_minutes=5),
    DriverLocation("d2", 40.7580, -73.9855, rating=4.2, acceptance_rate=0.80, idle_minutes=30),
    DriverLocation("d3", 40.7527, -73.9772, rating=4.8, acceptance_rate=0.98, idle_minutes=15),
    DriverLocation("d4", 40.7614, -73.9776, rating=3.5, acceptance_rate=0.70, idle_minutes=45),
    DriverLocation("d5", 40.7488, -73.9680, rating=4.7, acceptance_rate=0.92, idle_minutes=2),
]

PICKUP = RideRequest(
    request_id="req-001",
    pickup_lat=40.7505,
    pickup_lon=-73.9934,
    dropoff_lat=40.7580,
    dropoff_lon=-73.9855,
)


def demo_nearest_driver() -> None:
    """Show simple nearest-driver matching."""
    print("\n+------------------------------------------+")
    print("|   Demo: Nearest Driver Algorithm         |")
    print("+------------------------------------------+\n")

    nearest = find_nearest_driver(PICKUP, DRIVERS)
    if nearest:
        print(f"  Pickup: ({PICKUP.pickup_lat}, {PICKUP.pickup_lon})")
        print(f"  Nearest driver: {nearest.driver.driver_id}")
        print(f"  Distance: {nearest.distance_km:.3f} km")
        print(f"  ETA: {nearest.estimated_eta_minutes:.1f} minutes")

    print("\n  K=3 nearest drivers:")
    top3 = find_k_nearest_drivers(PICKUP, DRIVERS, k=3)
    for i, match in enumerate(top3, 1):
        print(f"    {i}. {match.driver.driver_id}: {match.distance_km:.3f} km, "
              f"ETA {match.estimated_eta_minutes:.1f} min")


def demo_scoring() -> None:
    """Show weighted scoring with different weight configurations."""
    print("\n+------------------------------------------+")
    print("|   Demo: Weighted Scoring Model           |")
    print("+------------------------------------------+\n")

    # Default weights (balanced)
    print("  === Balanced Weights (distance=0.4, rating=0.25, accept=0.2, idle=0.15) ===")
    scored = score_drivers(PICKUP, DRIVERS)
    for i, s in enumerate(scored, 1):
        print(f"    {i}. {s.driver.driver_id}: score={s.total_score:.4f} "
              f"(dist={s.distance_score:.2f}, rate={s.rating_score:.2f}, "
              f"accept={s.acceptance_score:.2f}, idle={s.idle_time_score:.2f})")

    # Distance-heavy weights
    print("\n  === Distance-Heavy (distance=0.8) ===")
    dist_weights = ScoringWeights(distance=0.80, rating=0.10, acceptance=0.05, idle_time=0.05)
    scored2 = score_drivers(PICKUP, DRIVERS, weights=dist_weights)
    for i, s in enumerate(scored2[:3], 1):
        print(f"    {i}. {s.driver.driver_id}: score={s.total_score:.4f} "
              f"(dist_km={s.distance_km:.3f})")

    # Fairness-heavy weights
    print("\n  === Fairness-Heavy (idle_time=0.60) ===")
    fair_weights = ScoringWeights(distance=0.15, rating=0.10, acceptance=0.15, idle_time=0.60)
    scored3 = score_drivers(PICKUP, DRIVERS, weights=fair_weights)
    for i, s in enumerate(scored3[:3], 1):
        print(f"    {i}. {s.driver.driver_id}: score={s.total_score:.4f} "
              f"(idle={s.driver.idle_minutes:.0f} min)")


def demo_hungarian() -> None:
    """Compare greedy vs optimal batch matching."""
    print("\n+------------------------------------------+")
    print("|   Demo: Hungarian vs Greedy Matching     |")
    print("+------------------------------------------+\n")

    # Create 3 requests at different locations
    requests = [
        RideRequest("r1", 40.7484, -73.9857, 40.7580, -73.9855),  # Empire State
        RideRequest("r2", 40.7527, -73.9772, 40.7614, -73.9776),  # Grand Central
        RideRequest("r3", 40.7614, -73.9776, 40.7488, -73.9680),  # Central Park S
    ]
    # Use first 3 drivers
    drivers = DRIVERS[:3]

    # Greedy matching
    greedy = greedy_match(requests, drivers)
    greedy_total = sum(a.distance_km for a in greedy)

    print("  Greedy matching (nearest-first):")
    for a in greedy:
        print(f"    {a.driver.driver_id} -> {a.request.request_id}: {a.distance_km:.4f} km")
    print(f"    Total distance: {greedy_total:.4f} km")

    # Hungarian (optimal) matching
    optimal = hungarian_match(requests, drivers)
    optimal_total = sum(a.distance_km for a in optimal)

    print("\n  Hungarian matching (optimal):")
    for a in optimal:
        print(f"    {a.driver.driver_id} -> {a.request.request_id}: {a.distance_km:.4f} km")
    print(f"    Total distance: {optimal_total:.4f} km")

    improvement = ((greedy_total - optimal_total) / greedy_total * 100) if greedy_total > 0 else 0
    print(f"\n  Improvement: {improvement:.1f}% less total distance with batch matching")


def main() -> None:
    print("=" * 50)
    print("  Module 09: Dispatch Algorithms")
    print("=" * 50)

    demo_nearest_driver()
    demo_scoring()
    demo_hungarian()

    print("\n[DONE] Module 09 demos complete!\n")


if __name__ == "__main__":
    main()
