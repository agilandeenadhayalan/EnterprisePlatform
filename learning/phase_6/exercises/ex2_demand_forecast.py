"""
Exercise 2: Inverse Distance Weighted Spatial Interpolation
========================================
Implement spatial interpolation to predict demand at an unknown location
based on demand values at known locations, weighted by inverse distance.

WHY THIS MATTERS:
Ride-hailing platforms need to estimate demand everywhere in a city, but
they only have direct measurements (actual ride requests) at specific
locations. Spatial interpolation fills in the gaps. IDW is the simplest
and most intuitive approach: locations closer to the target should have
more influence on the prediction than distant ones.

The power parameter controls how quickly influence decays with distance:
  - power=1: linear decay (gentle falloff, distant points still matter)
  - power=2: quadratic decay (default, good balance)
  - power=3+: rapid decay (only very close points matter)

Formula:
  predicted = sum(value_i / dist_i^p) / sum(1 / dist_i^p)

where dist_i is the Haversine distance from the target to known point i.

YOUR TASK:
Implement interpolate(target_lat, target_lng, known_points, power=2)
that returns the interpolated demand value.
"""

import math


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Compute great-circle distance in km between two lat/lng points."""
    R = 6371.0
    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlng / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def interpolate(
    target_lat: float,
    target_lng: float,
    known_points: list[tuple[float, float, float]],
    power: float = 2.0,
) -> float:
    """Inverse distance weighted interpolation.

    Args:
        target_lat: latitude of the target location.
        target_lng: longitude of the target location.
        known_points: list of (lat, lng, value) tuples for known locations.
        power: distance decay exponent (default 2.0).

    Returns:
        Interpolated value at the target location.

    Special cases:
        - If the target is exactly at a known point (distance < 0.001 km),
          return that point's value directly.
        - If known_points is empty, raise ValueError.

    Formula:
        result = sum(value_i / dist_i^power) / sum(1 / dist_i^power)
    """
    # YOUR CODE HERE (~15 lines)
    # Hints:
    # 1. Check for empty known_points
    # 2. For each known point, compute Haversine distance to target
    # 3. If any distance < 0.001, return that point's value immediately
    # 4. Compute weighted_sum = sum(value / dist^power)
    # 5. Compute weight_total = sum(1 / dist^power)
    # 6. Return weighted_sum / weight_total
    raise NotImplementedError("Implement interpolate")


# ── Verification ──


def _verify():
    """Run basic checks to verify your implementation."""

    # Test 1: Exact match — target at a known point
    known = [(0.0, 0.0, 100.0), (1.0, 0.0, 50.0)]
    result = interpolate(0.0, 0.0, known)
    assert result == 100.0, f"Expected 100.0 for exact match, got {result}"
    print("[PASS] Exact match returns known value")

    # Test 2: Midpoint is closer to arithmetic mean of nearby points
    known = [(0.0, 0.0, 100.0), (0.02, 0.0, 0.0)]  # ~2.2 km apart
    result = interpolate(0.01, 0.0, known)  # midpoint
    assert 40 < result < 60, f"Expected ~50 for equidistant, got {result}"
    print(f"[PASS] Midpoint interpolation: {result:.1f}")

    # Test 3: Closer point dominates
    known = [
        (0.0, 0.0, 100.0),   # very close
        (1.0, 0.0, 0.0),     # ~111 km away
    ]
    result = interpolate(0.001, 0.0, known)
    assert result > 90, f"Expected > 90 for close point dominance, got {result}"
    print(f"[PASS] Close point dominance: {result:.1f}")

    # Test 4: Higher power increases decay
    known = [(0.0, 0.0, 100.0), (0.1, 0.0, 0.0)]
    r1 = interpolate(0.05, 0.0, known, power=1)
    r2 = interpolate(0.05, 0.0, known, power=3)
    # Both should be valid, just different weights
    assert 0 < r1 < 100 and 0 < r2 < 100
    print(f"[PASS] Power=1: {r1:.1f}, Power=3: {r2:.1f}")

    # Test 5: Empty points raises ValueError
    try:
        interpolate(0.0, 0.0, [])
        assert False, "Should have raised ValueError"
    except ValueError:
        print("[PASS] Empty known_points raises ValueError")

    print("\nAll checks passed!")


if __name__ == "__main__":
    _verify()
