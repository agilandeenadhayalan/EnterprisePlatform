"""
City integration — dispatch, pricing, and ETA estimation.

WHY THIS MATTERS:
Dispatch, pricing, and ETA are the three core algorithms of a mobility
platform. Dispatch decides which driver serves which rider. Pricing
balances supply and demand through surge multipliers. ETA sets rider
expectations and influences conversion rates. Together, they determine
the platform's efficiency and user experience.

Key concepts:
  - Nearest dispatch: simplest strategy, assign closest idle driver
  - Scored dispatch: multi-factor scoring (distance, rating, history)
  - Dynamic pricing: surge multipliers based on supply/demand ratio
  - ETA estimation: distance / speed with traffic adjustment
"""

from dataclasses import dataclass, field


class DispatchPolicy:
    """Base class for dispatch policies.

    Subclasses implement different strategies for assigning drivers
    to ride requests.
    """

    def assign(self, request, available_drivers: list):
        """Assign a driver to a ride request.

        Args:
            request: RideRequest with pickup/dropoff positions
            available_drivers: list of idle DriverAgent objects

        Returns:
            driver_id of the assigned driver, or None if no driver available
        """
        raise NotImplementedError


class NearestDriverDispatch(DispatchPolicy):
    """Assign the closest idle driver by Euclidean distance.

    The simplest dispatch strategy. Works well when drivers are
    evenly distributed and all equally capable.
    """

    def assign(self, request, available_drivers: list):
        """Assign the driver closest to the pickup location.

        Returns the driver's id, or None if no drivers are available.
        """
        if not available_drivers:
            return None

        best = None
        best_dist = float('inf')
        for driver in available_drivers:
            dist = driver.position.distance_to(request.pickup)
            if dist < best_dist:
                best_dist = dist
                best = driver

        return best.id if best else None


class ScoredDispatch(DispatchPolicy):
    """Multi-factor dispatch using composite scoring.

    Scores each driver on distance (inverse), rating, and completion
    rate. This produces better outcomes than nearest-only because it
    considers driver quality alongside proximity.
    """

    def score(self, driver, request) -> float:
        """Calculate a composite score for a driver-request pair.

        Score = distance_score * 0.5 + rating_score * 0.3 + completion_score * 0.2

        distance_score: 1 / (1 + distance) — closer is better
        rating_score: driver.rating / 5.0 — normalized to [0, 1]
        completion_score: driver.completion_rate — already [0, 1]
        """
        dist = driver.position.distance_to(request.pickup)
        distance_score = 1.0 / (1.0 + dist)

        rating = getattr(driver, 'rating', 5.0)
        rating_score = rating / 5.0

        completion_rate = getattr(driver, 'completion_rate', 1.0)

        return distance_score * 0.5 + rating_score * 0.3 + completion_rate * 0.2

    def assign(self, request, available_drivers: list):
        """Assign the highest-scoring driver.

        Returns the driver's id, or None if no drivers are available.
        """
        if not available_drivers:
            return None

        best = max(available_drivers, key=lambda d: self.score(d, request))
        return best.id


class DynamicPricing:
    """Calculate ride fares with surge pricing.

    Base fare + per-km + per-min, multiplied by a surge factor
    that increases when demand exceeds supply.
    """

    def __init__(self, base_fare: float, per_km_rate: float, per_min_rate: float):
        """Initialize pricing model.

        Args:
            base_fare: flat fee per ride
            per_km_rate: cost per kilometer
            per_min_rate: cost per minute
        """
        self.base_fare = base_fare
        self.per_km_rate = per_km_rate
        self.per_min_rate = per_min_rate

    def calculate(
        self,
        distance_km: float,
        duration_min: float,
        surge_multiplier: float = 1.0,
    ) -> float:
        """Calculate total fare for a ride.

        fare = (base + distance * per_km + duration * per_min) * surge
        """
        raw_fare = (
            self.base_fare
            + distance_km * self.per_km_rate
            + duration_min * self.per_min_rate
        )
        return raw_fare * surge_multiplier

    def get_surge(self, supply: int, demand: int) -> float:
        """Calculate surge multiplier based on supply/demand ratio.

        If supply >= demand: no surge (1.0).
        Otherwise: surge = demand / supply, capped at 3.0.
        Returns 3.0 if supply is 0 and demand > 0.
        """
        if demand == 0:
            return 1.0
        if supply == 0:
            return 3.0
        ratio = demand / supply
        if ratio <= 1.0:
            return 1.0
        return min(ratio, 3.0)


class ETAEstimator:
    """Estimate time of arrival for a driver reaching a pickup.

    Uses distance / speed with an optional traffic factor that
    increases ETA during congestion.
    """

    def estimate(
        self,
        driver_position,
        pickup_position,
        average_speed: float,
        traffic_factor: float = 1.0,
    ) -> float:
        """Estimate ETA in seconds.

        ETA = (distance / speed) * traffic_factor.
        Traffic factor > 1.0 means congestion (slower).
        Returns float('inf') if speed is 0.
        """
        if average_speed == 0:
            return float('inf')
        distance = driver_position.distance_to(pickup_position)
        return (distance / average_speed) * traffic_factor


class CityOrchestrator:
    """Coordinate dispatch, pricing, and ETA for ride handling.

    Acts as the central coordinator: when a ride request comes in,
    it dispatches a driver, calculates the fare, and estimates ETA.
    """

    def __init__(self, dispatch_policy: DispatchPolicy, pricing: DynamicPricing, eta_estimator: ETAEstimator):
        self._dispatch = dispatch_policy
        self._pricing = pricing
        self._eta = eta_estimator
        self._completed = 0
        self._dispatched = 0

    def handle_request(self, request, drivers: list) -> dict:
        """Handle a ride request end-to-end.

        1. Dispatch a driver
        2. Calculate the fare
        3. Estimate ETA

        Args:
            request: RideRequest with pickup/dropoff
            drivers: list of available DriverAgent objects

        Returns:
            dict with driver_id, fare, eta_seconds, or None values if no driver
        """
        driver_id = self._dispatch.assign(request, drivers)

        if driver_id is None:
            return {"driver_id": None, "fare": None, "eta_seconds": None}

        self._dispatched += 1

        # Find the assigned driver
        driver = next((d for d in drivers if d.id == driver_id), None)

        # Calculate distance and duration estimates
        distance_km = request.pickup.distance_to(request.dropoff)
        duration_min = distance_km / 0.5 if distance_km > 0 else 1.0  # rough estimate

        fare = self._pricing.calculate(distance_km, duration_min)

        eta = self._eta.estimate(
            driver.position, request.pickup,
            average_speed=driver.speed if hasattr(driver, 'speed') else 1.0,
        )

        return {
            "driver_id": driver_id,
            "fare": fare,
            "eta_seconds": eta,
        }

    def get_summary(self) -> dict:
        """Return summary statistics for this orchestrator."""
        return {
            "dispatched": self._dispatched,
            "completed": self._completed,
        }
