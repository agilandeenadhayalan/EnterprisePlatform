"""
Driver scoring algorithm for dispatch decisions.

Computes a composite score for each candidate driver based on multiple
factors. Higher scores indicate a better match for the trip.

The formula weighs:
  - Proximity (closer is better)
  - Driver rating (higher is better)
  - Acceptance rate (more reliable is better)
  - Cancellation rate (lower is better)
"""


def score_driver(
    distance: float,
    rating: float,
    acceptance_rate: float,
    cancellation_rate: float,
) -> float:
    """
    Calculate a dispatch score for a driver candidate.

    Args:
        distance: Distance to pickup in miles (lower is better)
        rating: Driver rating 0-5 (higher is better)
        acceptance_rate: Historical acceptance rate 0-1 (higher is better)
        cancellation_rate: Historical cancellation rate 0-1 (lower is better)

    Returns:
        A float score where higher = better match. Range roughly 0-100.

    # TODO: Customize these weights based on your business priorities.
    #   - Increase distance_weight to prioritize faster pickups
    #   - Increase rating_weight to prioritize rider satisfaction
    #   - Increase acceptance_weight to prioritize reliable drivers
    #   - Increase cancellation_penalty to penalize flaky drivers
    #
    # Current defaults are balanced for a general ride-hailing use case.
    # Consider A/B testing different weight configurations in production.
    """
    # ── Weight configuration ──
    distance_weight = 30.0       # Max points from proximity
    rating_weight = 30.0         # Max points from rating
    acceptance_weight = 25.0     # Max points from acceptance rate
    cancellation_penalty = 15.0  # Max penalty from cancellation rate

    # ── Distance score: inverse relationship (closer = higher score) ──
    # Cap at 20 miles — beyond that, distance score is 0
    max_distance = 20.0
    clamped_distance = min(max(distance, 0.0), max_distance)
    distance_score = (1.0 - clamped_distance / max_distance) * distance_weight

    # ── Rating score: linear 0-5 mapped to weight ──
    clamped_rating = min(max(rating, 0.0), 5.0)
    rating_score = (clamped_rating / 5.0) * rating_weight

    # ── Acceptance rate score: linear 0-1 mapped to weight ──
    clamped_acceptance = min(max(acceptance_rate, 0.0), 1.0)
    acceptance_score = clamped_acceptance * acceptance_weight

    # ── Cancellation penalty: linear 0-1, higher rate = bigger penalty ──
    clamped_cancellation = min(max(cancellation_rate, 0.0), 1.0)
    cancel_score = clamped_cancellation * cancellation_penalty

    total = distance_score + rating_score + acceptance_score - cancel_score

    # Floor at 0 — a driver can't have a negative score
    return round(max(total, 0.0), 2)
