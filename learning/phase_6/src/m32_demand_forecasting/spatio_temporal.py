"""
Grid-Based Spatial Modeling — Cells, neighbors, and spatial statistics.

WHY THIS MATTERS:
Ride-hailing platforms divide cities into spatial grid cells and forecast
demand per cell per time bucket. Understanding spatial autocorrelation
(nearby cells have similar demand) and temporal patterns (rush hours,
weekends) is essential for accurate predictions.

Key concepts:
  - GridCell: a geographic tile with base demand characteristics.
  - TimeSlot: a time bucket (hour range + day of week).
  - SpatioTemporalGrid: the full grid with spatial queries and stats.
  - Haversine distance: great-circle distance between lat/lng points.
  - Moran's I: measures spatial autocorrelation (do nearby cells behave
    similarly?).
  - Inverse Distance Weighting: interpolate unknown demand from known
    neighbors, weighting by inverse distance.
"""

import math


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Compute great-circle distance in km between two lat/lng points.

    Uses the Haversine formula. This is the standard way to compute
    distances on Earth's surface without projecting to a flat coordinate
    system. Accurate for distances up to ~1000 km.
    """
    R = 6371.0  # Earth radius in km
    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlng / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class GridCell:
    """A spatial cell in the demand grid.

    Each cell covers a small geographic area (typically 500m x 500m in
    production systems like Uber's H3 hexagons). The base_demand reflects
    average demand without any time-of-day or weather adjustments.
    """

    def __init__(self, id: str, zone_name: str, lat: float, lng: float, base_demand: float = 0.0):
        self.id = id
        self.zone_name = zone_name
        self.lat = lat
        self.lng = lng
        self.base_demand = base_demand


class TimeSlot:
    """A time bucket for demand aggregation.

    Demand varies dramatically by time of day and day of week. Time slots
    let us model these patterns separately (e.g., Monday 8-9 AM vs.
    Saturday 8-9 AM have very different demand profiles).
    """

    def __init__(self, start_hour: int, end_hour: int, day_of_week: int):
        if not 0 <= start_hour <= 23:
            raise ValueError(f"start_hour must be 0-23, got {start_hour}")
        if not 0 <= end_hour <= 23:
            raise ValueError(f"end_hour must be 0-23, got {end_hour}")
        if not 0 <= day_of_week <= 6:
            raise ValueError(f"day_of_week must be 0-6, got {day_of_week}")
        self.start_hour = start_hour
        self.end_hour = end_hour
        self.day_of_week = day_of_week

    @property
    def duration_hours(self) -> int:
        """Duration of the time slot in hours."""
        if self.end_hour >= self.start_hour:
            return self.end_hour - self.start_hour
        return (24 - self.start_hour) + self.end_hour

    def is_weekend(self) -> bool:
        """Check if this slot falls on a weekend (Saturday=5, Sunday=6)."""
        return self.day_of_week >= 5


class SpatioTemporalGrid:
    """A grid of spatial cells with demand data and spatial queries.

    Supports neighbor discovery by distance, spatial autocorrelation
    analysis, temporal pattern detection, and inverse distance weighted
    interpolation.
    """

    def __init__(self):
        self._cells: dict[str, GridCell] = {}

    def add_cell(self, cell: GridCell) -> None:
        """Add a cell to the grid."""
        self._cells[cell.id] = cell

    def get_cell(self, cell_id: str) -> GridCell:
        """Return the cell with the given id, or raise KeyError."""
        if cell_id not in self._cells:
            raise KeyError(f"Cell '{cell_id}' not found")
        return self._cells[cell_id]

    @property
    def cell_count(self) -> int:
        """Number of cells in the grid."""
        return len(self._cells)

    def get_neighbors(self, cell_id: str, radius_km: float) -> list[GridCell]:
        """Return cells within radius_km of the given cell.

        Uses Haversine distance. Does not include the cell itself.
        """
        center = self.get_cell(cell_id)
        neighbors = []
        for cid, cell in self._cells.items():
            if cid == cell_id:
                continue
            dist = _haversine(center.lat, center.lng, cell.lat, cell.lng)
            if dist <= radius_km:
                neighbors.append(cell)
        return neighbors

    def spatial_autocorrelation(self, cell_id: str, demands: dict[str, float]) -> float:
        """Simplified Moran's I for a single cell.

        Measures the correlation between a cell's demand and the mean
        demand of its neighbors (within 5 km). Returns a value in [-1, 1]:
          +1 means the cell has similar demand to its neighbors (positive SA)
          -1 means the cell differs from its neighbors (negative SA)
           0 means no spatial pattern

        Formula: (cell_demand - global_mean) * (neighbor_mean - global_mean) / variance
        """
        if cell_id not in demands:
            raise ValueError(f"No demand data for cell '{cell_id}'")

        all_demands = list(demands.values())
        if len(all_demands) < 2:
            return 0.0

        global_mean = sum(all_demands) / len(all_demands)
        variance = sum((d - global_mean) ** 2 for d in all_demands) / len(all_demands)
        if variance == 0:
            return 0.0

        neighbors = self.get_neighbors(cell_id, radius_km=5.0)
        neighbor_demands = [demands[n.id] for n in neighbors if n.id in demands]
        if not neighbor_demands:
            return 0.0

        neighbor_mean = sum(neighbor_demands) / len(neighbor_demands)
        cell_demand = demands[cell_id]

        return (cell_demand - global_mean) * (neighbor_mean - global_mean) / variance

    def temporal_pattern(self, cell_id: str, hourly_demands: list[float]) -> dict:
        """Detect temporal pattern in hourly demand data.

        Analyzes a 24-element list of hourly demands to find peak and
        trough hours, amplitude, and mean. This reveals the daily rhythm
        of demand for a cell.

        Returns:
            {"peak_hour": int, "trough_hour": int, "amplitude": float, "mean": float}
        """
        if not hourly_demands:
            raise ValueError("hourly_demands must be non-empty")
        if cell_id not in self._cells:
            raise KeyError(f"Cell '{cell_id}' not found")

        mean = sum(hourly_demands) / len(hourly_demands)
        peak_hour = hourly_demands.index(max(hourly_demands))
        trough_hour = hourly_demands.index(min(hourly_demands))
        amplitude = max(hourly_demands) - min(hourly_demands)

        return {
            "peak_hour": peak_hour,
            "trough_hour": trough_hour,
            "amplitude": amplitude,
            "mean": mean,
        }

    def interpolate_demand(self, cell_id: str, known_demands: dict[str, float]) -> float:
        """Inverse distance weighted interpolation from known cells.

        Predicts demand for a cell based on demands of other cells,
        weighted by inverse distance. Closer cells have more influence.

        Formula: sum(demand_i / dist_i) / sum(1 / dist_i)

        Raises ValueError if no known demand data is available.
        """
        target = self.get_cell(cell_id)
        weighted_sum = 0.0
        weight_total = 0.0

        for known_id, demand in known_demands.items():
            if known_id == cell_id:
                continue
            if known_id not in self._cells:
                continue
            known_cell = self._cells[known_id]
            dist = _haversine(target.lat, target.lng, known_cell.lat, known_cell.lng)
            if dist < 0.001:  # avoid division by zero
                return demand
            w = 1.0 / dist
            weighted_sum += w * demand
            weight_total += w

        if weight_total == 0:
            raise ValueError(f"No known demand data to interpolate for cell '{cell_id}'")

        return weighted_sum / weight_total
