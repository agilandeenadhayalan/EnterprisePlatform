"""
H3 Hexagonal Grid (Simulated)
================================

Simulates the H3 hierarchical hexagonal grid system developed by Uber
for spatial indexing and zone management.

WHY hexagonal grids:
- Hexagons have uniform distance to all neighbors (unlike squares)
- No diagonal distortion — every neighboring cell edge-shares
- Better approximation of circles (surge zones, service areas)
- Hierarchical: each hex contains 7 child hexes at next resolution

Resolution levels (approximate):
    Res 0:  ~1,107 km edge length (global)
    Res 3:  ~59 km edge length (state-level)
    Res 5:  ~8 km edge length (city-level)
    Res 7:  ~1.2 km edge length (neighborhood, ~5.16 km^2)
    Res 9:  ~174 m edge length (block-level, ~0.105 km^2)
    Res 11: ~24 m edge length (building-level)
    Res 15: ~0.5 m edge length (maximum resolution)

Note: This is a pure-Python SIMULATION, not the real H3 library.
It demonstrates the concepts with simplified grid math.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .haversine import GeoPoint


# ── Resolution configuration ──
# Approximate edge length in km for each resolution
RESOLUTION_EDGE_KM: dict[int, float] = {
    0: 1107.71,
    1: 418.68,
    2: 158.24,
    3: 59.81,
    4: 22.61,
    5: 8.54,
    6: 3.23,
    7: 1.22,
    8: 0.461,
    9: 0.174,
    10: 0.066,
    11: 0.025,
    12: 0.009,
}


@dataclass(frozen=True)
class H3Cell:
    """
    A simulated H3 hexagonal cell.

    In the real H3 library, cells are identified by 64-bit integers.
    Here we use a simplified string ID based on grid coordinates.
    """
    cell_id: str
    resolution: int
    center_lat: float
    center_lon: float
    edge_length_km: float

    @property
    def area_km2(self) -> float:
        """Approximate area of a regular hexagon."""
        return 2.598 * self.edge_length_km ** 2


def lat_lon_to_cell(
    lat: float,
    lon: float,
    resolution: int = 9,
) -> H3Cell:
    """
    Map a lat/lon point to a simulated H3 cell.

    This approximates H3's behavior using a flat grid (not icosahedron).
    Real H3 projects onto an icosahedron face for global uniformity.

    The cell ID encodes the resolution and grid coordinates.
    """
    if resolution not in RESOLUTION_EDGE_KM:
        raise ValueError(f"Resolution must be 0-12, got {resolution}")

    edge_km = RESOLUTION_EDGE_KM[resolution]

    # Convert to approximate grid coordinates
    # Hex grid: offset every other row by half a cell width
    hex_width = edge_km * math.sqrt(3)  # Width of hex in km
    hex_height = edge_km * 2            # Height of hex in km

    # Approximate km per degree
    km_per_lat = 111.32
    km_per_lon = 111.32 * math.cos(math.radians(lat))

    # Grid coordinates
    col = int((lon * km_per_lon) / hex_width) if hex_width > 0 else 0
    row_offset = 0.5 if col % 2 == 1 else 0.0
    row = int((lat * km_per_lat + row_offset * hex_height) / (hex_height * 0.75)) if hex_height > 0 else 0

    # Cell center (snap to grid)
    center_lon = (col * hex_width) / km_per_lon if km_per_lon > 0 else lon
    center_lat = (row * hex_height * 0.75 - row_offset * hex_height) / km_per_lat

    cell_id = f"h3_{resolution:02d}_{row:+08d}_{col:+08d}"

    return H3Cell(
        cell_id=cell_id,
        resolution=resolution,
        center_lat=round(center_lat, 6),
        center_lon=round(center_lon, 6),
        edge_length_km=edge_km,
    )


def get_neighbors(cell: H3Cell) -> list[H3Cell]:
    """
    Get the 6 neighboring cells of a hexagonal cell.

    In a hex grid, each cell has exactly 6 neighbors that share an edge.
    This is a key advantage over square grids (which have 4 edge + 4 corner).
    """
    edge_km = cell.edge_length_km
    hex_width = edge_km * math.sqrt(3)
    hex_height = edge_km * 2

    km_per_lat = 111.32
    km_per_lon = 111.32 * math.cos(math.radians(cell.center_lat))

    # 6 neighbor offsets for a hex grid (flat-top hexagons)
    dlat = (hex_height * 0.75) / km_per_lat
    dlon = hex_width / km_per_lon if km_per_lon > 0 else 0
    half_dlon = dlon / 2

    offsets = [
        (0, dlon),           # East
        (0, -dlon),          # West
        (dlat, half_dlon),   # Northeast
        (dlat, -half_dlon),  # Northwest
        (-dlat, half_dlon),  # Southeast
        (-dlat, -half_dlon), # Southwest
    ]

    neighbors: list[H3Cell] = []
    for dlat_off, dlon_off in offsets:
        nlat = cell.center_lat + dlat_off
        nlon = cell.center_lon + dlon_off

        # Clamp to valid range
        nlat = max(-90, min(90, nlat))
        nlon = max(-180, min(180, nlon))

        neighbor = lat_lon_to_cell(nlat, nlon, cell.resolution)
        if neighbor.cell_id != cell.cell_id:
            neighbors.append(neighbor)

    # Deduplicate by cell_id
    seen: set[str] = set()
    unique: list[H3Cell] = []
    for n in neighbors:
        if n.cell_id not in seen:
            seen.add(n.cell_id)
            unique.append(n)

    return unique


def cells_in_radius(
    center: GeoPoint,
    radius_km: float,
    resolution: int = 9,
) -> list[H3Cell]:
    """
    Find all H3 cells within a radius of a center point.

    Useful for: "Find all surge zones within 5km of this location."

    This is a simplified ring search — real H3 uses kRing/hexRange.
    """
    center_cell = lat_lon_to_cell(center.lat, center.lon, resolution)
    result: dict[str, H3Cell] = {center_cell.cell_id: center_cell}

    # BFS outward from center
    frontier = [center_cell]
    visited: set[str] = {center_cell.cell_id}

    while frontier:
        next_frontier: list[H3Cell] = []
        for cell in frontier:
            for neighbor in get_neighbors(cell):
                if neighbor.cell_id in visited:
                    continue
                visited.add(neighbor.cell_id)

                # Check if neighbor center is within radius
                from .haversine import haversine
                dist = haversine(center, GeoPoint(neighbor.center_lat, neighbor.center_lon))
                if dist <= radius_km:
                    result[neighbor.cell_id] = neighbor
                    next_frontier.append(neighbor)

        frontier = next_frontier

    return list(result.values())


def compare_resolutions(lat: float, lon: float) -> list[H3Cell]:
    """
    Show the same point at different resolution levels.

    Demonstrates the hierarchical nature of H3 — zooming in reveals
    finer-grained cells nested within coarser ones.
    """
    resolutions = [5, 7, 9, 11]
    return [lat_lon_to_cell(lat, lon, res) for res in resolutions]
