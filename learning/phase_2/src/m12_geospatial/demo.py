"""
Demo: Geospatial Computing
============================

Run: python -m learning.phase_2.src.m12_geospatial.demo
"""

from .haversine import (
    GeoPoint,
    haversine,
    bearing,
    point_in_polygon,
    bounding_box,
    destination_point,
)
from .h3_grid import (
    lat_lon_to_cell,
    get_neighbors,
    compare_resolutions,
)
from .geohash import (
    encode,
    decode,
    neighbors,
)


# NYC landmarks
EMPIRE_STATE = GeoPoint(40.7484, -73.9857)
TIMES_SQUARE = GeoPoint(40.7580, -73.9855)
GRAND_CENTRAL = GeoPoint(40.7527, -73.9772)
CENTRAL_PARK_S = GeoPoint(40.7644, -73.9730)
STATUE_LIBERTY = GeoPoint(40.6892, -74.0445)


def demo_haversine() -> None:
    """Show distance and bearing calculations."""
    print("\n+------------------------------------------+")
    print("|   Demo: Haversine Distance & Bearing     |")
    print("+------------------------------------------+\n")

    pairs = [
        ("Empire State", EMPIRE_STATE, "Times Square", TIMES_SQUARE),
        ("Empire State", EMPIRE_STATE, "Grand Central", GRAND_CENTRAL),
        ("Empire State", EMPIRE_STATE, "Central Park S", CENTRAL_PARK_S),
        ("Empire State", EMPIRE_STATE, "Statue of Liberty", STATUE_LIBERTY),
    ]

    print(f"  {'From':>16} -> {'To':>18} | {'Distance':>10} | {'Bearing':>10}")
    print(f"  {'----':>16}    {'--':>18} | {'--------':>10} | {'-------':>10}")

    for name1, p1, name2, p2 in pairs:
        dist = haversine(p1, p2)
        brng = bearing(p1, p2)
        direction = _bearing_to_direction(brng)
        print(f"  {name1:>16} -> {name2:>18} | {dist:>8.3f} km | {brng:>6.1f} ({direction})")

    # Destination point
    print(f"\n  From Empire State, travel 2km due north:")
    dest = destination_point(EMPIRE_STATE, 0, 2.0)
    print(f"    Destination: ({dest.lat}, {dest.lon})")
    verify_dist = haversine(EMPIRE_STATE, dest)
    print(f"    Verify distance: {verify_dist:.3f} km")


def demo_point_in_polygon() -> None:
    """Show point-in-polygon testing."""
    print("\n+------------------------------------------+")
    print("|   Demo: Point-in-Polygon (Surge Zone)    |")
    print("+------------------------------------------+\n")

    # Define a rectangular "Midtown surge zone"
    midtown_zone = [
        GeoPoint(40.7450, -73.9950),  # SW
        GeoPoint(40.7450, -73.9700),  # SE
        GeoPoint(40.7650, -73.9700),  # NE
        GeoPoint(40.7650, -73.9950),  # NW
    ]

    test_points = [
        ("Empire State", EMPIRE_STATE),
        ("Times Square", TIMES_SQUARE),
        ("Grand Central", GRAND_CENTRAL),
        ("Statue of Liberty", STATUE_LIBERTY),
    ]

    print("  Midtown Surge Zone (40.745-40.765 lat, -73.995--73.970 lon)")
    for name, point in test_points:
        inside = point_in_polygon(point, midtown_zone)
        symbol = "INSIDE" if inside else "outside"
        print(f"    {name:>18}: ({point.lat}, {point.lon}) -> {symbol}")


def demo_h3_grid() -> None:
    """Show H3 hexagonal grid indexing."""
    print("\n+------------------------------------------+")
    print("|   Demo: H3 Hexagonal Grid                |")
    print("+------------------------------------------+\n")

    # Map Times Square at different resolutions
    print("  Times Square (40.7580, -73.9855) at different resolutions:")
    cells = compare_resolutions(TIMES_SQUARE.lat, TIMES_SQUARE.lon)
    for cell in cells:
        print(f"    Res {cell.resolution:>2}: edge={cell.edge_length_km:>8.3f} km, "
              f"area={cell.area_km2:>10.4f} km^2, id={cell.cell_id}")

    # Show neighbors at resolution 9
    print(f"\n  Neighbors of Times Square cell (res 9):")
    cell = lat_lon_to_cell(TIMES_SQUARE.lat, TIMES_SQUARE.lon, resolution=9)
    nbrs = get_neighbors(cell)
    print(f"    Center: {cell.cell_id}")
    for i, n in enumerate(nbrs):
        print(f"    Neighbor {i+1}: {n.cell_id}")

    print(f"\n  KEY INSIGHT: Each hex has exactly 6 neighbors (uniform)")
    print(f"  Square grids have 4 edge-neighbors + 4 diagonal = non-uniform")


def demo_geohash() -> None:
    """Show geohash encoding/decoding."""
    print("\n+------------------------------------------+")
    print("|   Demo: Geohash Encoding                 |")
    print("+------------------------------------------+\n")

    # Encode NYC landmarks
    landmarks = [
        ("Empire State", EMPIRE_STATE),
        ("Times Square", TIMES_SQUARE),
        ("Grand Central", GRAND_CENTRAL),
        ("Statue of Liberty", STATUE_LIBERTY),
    ]

    print("  Encoding NYC landmarks (precision 7):")
    for name, point in landmarks:
        gh = encode(point.lat, point.lon, precision=7)
        print(f"    {name:>20}: {gh}")

    # Show precision levels
    print(f"\n  Empire State at different precisions:")
    for prec in [3, 5, 7, 9]:
        gh = encode(EMPIRE_STATE.lat, EMPIRE_STATE.lon, precision=prec)
        bounds = decode(gh)
        print(f"    Precision {prec}: {gh:>12} ({bounds.width_km:.3f} km x {bounds.height_km:.3f} km)")

    # Show prefix property
    gh9 = encode(EMPIRE_STATE.lat, EMPIRE_STATE.lon, precision=9)
    print(f"\n  Prefix property (nearby points share prefixes):")
    print(f"    Empire State (p=9): {gh9}")
    print(f"    Empire State (p=7): {gh9[:7]} <- prefix of p=9")
    print(f"    Empire State (p=5): {gh9[:5]} <- prefix of p=7")

    # Show neighbors
    gh = encode(TIMES_SQUARE.lat, TIMES_SQUARE.lon, precision=7)
    nbrs = neighbors(gh)
    print(f"\n  Neighbors of Times Square ({gh}):")
    for direction, neighbor_gh in nbrs.items():
        print(f"    {direction:>3}: {neighbor_gh}")


def demo_comparison() -> None:
    """Compare Haversine, H3, and Geohash approaches."""
    print("\n+------------------------------------------+")
    print("|   Demo: System Comparison                |")
    print("+------------------------------------------+\n")

    lat, lon = TIMES_SQUARE.lat, TIMES_SQUARE.lon

    print(f"  Point: Times Square ({lat}, {lon})")
    print(f"\n  {'System':>12} | {'ID/Value':>30} | {'Use Case':>25}")
    print(f"  {'------':>12} | {'--------':>30} | {'--------':>25}")

    dist = haversine(TIMES_SQUARE, EMPIRE_STATE)
    print(f"  {'Haversine':>12} | {f'{dist:.3f} km':>30} | {'Point-to-point distance':>25}")

    cell = lat_lon_to_cell(lat, lon, 9)
    print(f"  {'H3 (res=9)':>12} | {cell.cell_id:>30} | {'Zone management':>25}")

    gh = encode(lat, lon, 7)
    print(f"  {'Geohash (7)':>12} | {gh:>30} | {'Database indexing':>25}")

    print(f"\n  When to use each:")
    print(f"    Haversine: Exact distance between two known points")
    print(f"    H3:        Zone-based analytics, surge pricing, supply tracking")
    print(f"    Geohash:   Proximity searches in databases (SQL LIKE 'dr5r%')")


def _bearing_to_direction(brng: float) -> str:
    """Convert bearing degrees to cardinal direction."""
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    idx = round(brng / 45) % 8
    return directions[idx]


def main() -> None:
    print("=" * 50)
    print("  Module 12: Geospatial Computing")
    print("=" * 50)

    demo_haversine()
    demo_point_in_polygon()
    demo_h3_grid()
    demo_geohash()
    demo_comparison()

    print("\n[DONE] Module 12 demos complete!\n")


if __name__ == "__main__":
    main()
