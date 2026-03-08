"""
Hungarian Algorithm — Optimal Batch Matching
==============================================

Assigns N ride requests to N drivers to minimize total distance.
This is the assignment problem, solved optimally by the Hungarian
algorithm in O(n^3) time.

WHY batch matching over individual greedy matching:
- Greedy (nearest-driver) makes locally optimal choices that can be
  globally suboptimal. Example:
    Driver A is 1km from Request 1, 5km from Request 2
    Driver B is 2km from Request 1, 2km from Request 2
    Greedy assigns A->1 (1km), leaving B->2 (2km) = 3km total
    Optimal assigns A->2 (5km)... wait, that's worse.
    Actually: A->1 (1km) + B->2 (2km) = 3km vs A->2 (5km) + B->1 (2km) = 7km
    Better example: three drivers, three requests where greedy fails.

- Batch matching waits briefly, collects requests, and finds the
  globally optimal assignment.

TRADE-OFFS:
- [+] Globally optimal total distance
- [+] Fair distribution of work
- [-] Requires batching (adds latency, typically 2-5 seconds)
- [-] O(n^3) complexity (fine for n < 1000)
- [-] Doesn't handle unequal counts naturally (needs padding)

Implementation: Simplified Hungarian algorithm using cost matrix.
"""

from __future__ import annotations

from dataclasses import dataclass
from .nearest_driver import (
    DriverLocation,
    RideRequest,
    haversine_distance,
)


@dataclass
class Assignment:
    """Result of assigning a driver to a request."""
    driver: DriverLocation
    request: RideRequest
    distance_km: float


def build_cost_matrix(
    requests: list[RideRequest],
    drivers: list[DriverLocation],
) -> list[list[float]]:
    """
    Build a cost matrix where cost[i][j] = distance from driver i to request j.

    Rows = drivers, Columns = requests.
    """
    matrix: list[list[float]] = []
    for driver in drivers:
        row: list[float] = []
        for request in requests:
            dist = haversine_distance(
                driver.lat, driver.lon,
                request.pickup_lat, request.pickup_lon,
            )
            row.append(dist)
        matrix.append(row)
    return matrix


def _hungarian_solve(cost_matrix: list[list[float]]) -> list[tuple[int, int]]:
    """
    Solve the assignment problem using a simplified Hungarian algorithm.

    This implementation handles rectangular matrices by padding with
    high-cost dummy entries, then applies the Hungarian method.

    Returns list of (row_index, col_index) assignments.
    """
    n_rows = len(cost_matrix)
    n_cols = len(cost_matrix[0]) if cost_matrix else 0

    if n_rows == 0 or n_cols == 0:
        return []

    # Pad to square matrix if needed
    n = max(n_rows, n_cols)
    INF = float("inf")

    # Create padded square cost matrix
    padded: list[list[float]] = []
    for i in range(n):
        row: list[float] = []
        for j in range(n):
            if i < n_rows and j < n_cols:
                row.append(cost_matrix[i][j])
            else:
                row.append(INF)
        padded.append(row)

    # Hungarian algorithm (Kuhn-Munkres)
    # Uses the potential (label) based approach
    u = [0.0] * (n + 1)   # potential for rows
    v = [0.0] * (n + 1)   # potential for cols
    p = [0] * (n + 1)      # assignment: col -> row
    way = [0] * (n + 1)    # path tracking

    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        min_v = [INF] * (n + 1)
        used = [False] * (n + 1)

        while True:
            used[j0] = True
            i0 = p[j0]
            delta = INF
            j1 = -1

            for j in range(1, n + 1):
                if not used[j]:
                    cur = padded[i0 - 1][j - 1] - u[i0] - v[j]
                    if cur < min_v[j]:
                        min_v[j] = cur
                        way[j] = j0
                    if min_v[j] < delta:
                        delta = min_v[j]
                        j1 = j

            if j1 == -1:
                break

            for j in range(n + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    min_v[j] -= delta

            j0 = j1
            if p[j0] == 0:
                break

        # Update assignment along the augmenting path
        while j0 != 0:
            p[j0] = p[way[j0]]
            j0 = way[j0]

    # Extract assignments (col -> row mapping, 1-indexed)
    assignments: list[tuple[int, int]] = []
    for j in range(1, n + 1):
        if p[j] != 0:
            row_idx = p[j] - 1
            col_idx = j - 1
            # Only include valid (non-padded) assignments
            if row_idx < n_rows and col_idx < n_cols:
                assignments.append((row_idx, col_idx))

    return assignments


def hungarian_match(
    requests: list[RideRequest],
    drivers: list[DriverLocation],
) -> list[Assignment]:
    """
    Optimally assign drivers to requests using the Hungarian algorithm.

    Minimizes total distance across all assignments.
    Handles unequal numbers of drivers and requests.

    Returns list of Assignment objects, sorted by distance.
    """
    if not requests or not drivers:
        return []

    available = [d for d in drivers if d.is_available]
    if not available:
        return []

    cost_matrix = build_cost_matrix(requests, available)
    pairs = _hungarian_solve(cost_matrix)

    assignments: list[Assignment] = []
    for driver_idx, request_idx in pairs:
        driver = available[driver_idx]
        request = requests[request_idx]
        dist = cost_matrix[driver_idx][request_idx]
        assignments.append(Assignment(
            driver=driver,
            request=request,
            distance_km=round(dist, 4),
        ))

    assignments.sort(key=lambda a: a.distance_km)
    return assignments


def greedy_match(
    requests: list[RideRequest],
    drivers: list[DriverLocation],
) -> list[Assignment]:
    """
    Greedy baseline: assign each request to the nearest available driver.

    This is the naive approach — compare with hungarian_match to see
    why batch optimization matters.
    """
    available = list(d for d in drivers if d.is_available)
    assigned_drivers: set[str] = set()
    assignments: list[Assignment] = []

    for request in requests:
        best_dist = float("inf")
        best_driver: DriverLocation | None = None

        for driver in available:
            if driver.driver_id in assigned_drivers:
                continue
            dist = haversine_distance(
                driver.lat, driver.lon,
                request.pickup_lat, request.pickup_lon,
            )
            if dist < best_dist:
                best_dist = dist
                best_driver = driver

        if best_driver is not None:
            assigned_drivers.add(best_driver.driver_id)
            assignments.append(Assignment(
                driver=best_driver,
                request=request,
                distance_km=round(best_dist, 4),
            ))

    return assignments
