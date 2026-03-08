"""Tests for Module 09: Dispatch Algorithms."""

import pytest

from learning.phase_2.src.m09_dispatch_algorithms.nearest_driver import (
    DriverLocation,
    RideRequest,
    haversine_distance,
    find_nearest_driver,
    find_k_nearest_drivers,
)
from learning.phase_2.src.m09_dispatch_algorithms.scoring import (
    ScoringWeights,
    score_drivers,
    normalize_distance,
    normalize_rating,
    normalize_idle_time,
)
from learning.phase_2.src.m09_dispatch_algorithms.hungarian import (
    hungarian_match,
    greedy_match,
    build_cost_matrix,
)


SAMPLE_DRIVERS = [
    DriverLocation("d1", 40.7484, -73.9857, rating=4.9, acceptance_rate=0.95, idle_minutes=5),
    DriverLocation("d2", 40.7580, -73.9855, rating=4.2, acceptance_rate=0.80, idle_minutes=30),
    DriverLocation("d3", 40.7527, -73.9772, rating=4.8, acceptance_rate=0.98, idle_minutes=15),
]

SAMPLE_REQUEST = RideRequest("r1", 40.7505, -73.9934, 40.7580, -73.9855)


class TestHaversine:
    def test_zero_distance(self):
        dist = haversine_distance(40.7484, -73.9857, 40.7484, -73.9857)
        assert dist == pytest.approx(0.0, abs=0.001)

    def test_known_distance(self):
        # Empire State to Times Square: ~1.08 km
        dist = haversine_distance(40.7484, -73.9857, 40.7580, -73.9855)
        assert 0.5 < dist < 2.0  # Reasonable range

    def test_symmetry(self):
        d1 = haversine_distance(40.7484, -73.9857, 40.7580, -73.9855)
        d2 = haversine_distance(40.7580, -73.9855, 40.7484, -73.9857)
        assert d1 == pytest.approx(d2, abs=0.0001)


class TestNearestDriver:
    def test_find_nearest(self):
        match = find_nearest_driver(SAMPLE_REQUEST, SAMPLE_DRIVERS)
        assert match is not None
        assert match.driver.driver_id in ["d1", "d2", "d3"]

    def test_no_available_drivers(self):
        unavailable = [DriverLocation("d1", 40.7484, -73.9857, is_available=False)]
        match = find_nearest_driver(SAMPLE_REQUEST, unavailable)
        assert match is None

    def test_k_nearest(self):
        matches = find_k_nearest_drivers(SAMPLE_REQUEST, SAMPLE_DRIVERS, k=2)
        assert len(matches) == 2
        # First match should be closer than second
        assert matches[0].distance_km <= matches[1].distance_km

    def test_k_larger_than_available(self):
        matches = find_k_nearest_drivers(SAMPLE_REQUEST, SAMPLE_DRIVERS, k=10)
        assert len(matches) == 3  # Only 3 drivers available

    def test_eta_is_positive(self):
        match = find_nearest_driver(SAMPLE_REQUEST, SAMPLE_DRIVERS)
        assert match is not None
        assert match.estimated_eta_minutes > 0


class TestScoring:
    def test_normalize_distance_closer_is_higher(self):
        assert normalize_distance(0.0) > normalize_distance(5.0)

    def test_normalize_distance_at_max(self):
        assert normalize_distance(10.0, max_distance_km=10.0) == pytest.approx(0.0)

    def test_normalize_rating(self):
        assert normalize_rating(5.0) == pytest.approx(1.0)
        assert normalize_rating(1.0) == pytest.approx(0.0)
        assert normalize_rating(3.0) == pytest.approx(0.5)

    def test_normalize_idle_time(self):
        assert normalize_idle_time(60.0, 60.0) == pytest.approx(1.0)
        assert normalize_idle_time(0.0) == pytest.approx(0.0)

    def test_score_drivers_returns_sorted(self):
        scored = score_drivers(SAMPLE_REQUEST, SAMPLE_DRIVERS)
        assert len(scored) > 0
        # Sorted by score descending
        for i in range(len(scored) - 1):
            assert scored[i].total_score >= scored[i + 1].total_score

    def test_distance_heavy_weights(self):
        weights = ScoringWeights(distance=1.0, rating=0.0, acceptance=0.0, idle_time=0.0)
        scored = score_drivers(SAMPLE_REQUEST, SAMPLE_DRIVERS, weights=weights)
        # With pure distance weights, closest driver should be first
        if len(scored) >= 2:
            assert scored[0].distance_km <= scored[1].distance_km


class TestHungarian:
    def test_cost_matrix_dimensions(self):
        requests = [SAMPLE_REQUEST]
        matrix = build_cost_matrix(requests, SAMPLE_DRIVERS)
        assert len(matrix) == 3       # 3 drivers (rows)
        assert len(matrix[0]) == 1    # 1 request (columns)

    def test_hungarian_single_assignment(self):
        requests = [SAMPLE_REQUEST]
        assignments = hungarian_match(requests, SAMPLE_DRIVERS)
        assert len(assignments) == 1

    def test_hungarian_multiple_assignments(self):
        requests = [
            RideRequest("r1", 40.7484, -73.9857, 40.7580, -73.9855),
            RideRequest("r2", 40.7580, -73.9855, 40.7484, -73.9857),
        ]
        assignments = hungarian_match(requests, SAMPLE_DRIVERS)
        assert len(assignments) == 2
        # All assignments should have different drivers
        driver_ids = [a.driver.driver_id for a in assignments]
        assert len(set(driver_ids)) == 2

    def test_greedy_match(self):
        requests = [SAMPLE_REQUEST]
        assignments = greedy_match(requests, SAMPLE_DRIVERS)
        assert len(assignments) == 1

    def test_empty_input(self):
        assert hungarian_match([], SAMPLE_DRIVERS) == []
        assert hungarian_match([SAMPLE_REQUEST], []) == []
