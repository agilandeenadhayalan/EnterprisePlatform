"""Tests for Module 12: Geospatial Computing."""

import math
import pytest

from learning.phase_2.src.m12_geospatial.haversine import (
    GeoPoint,
    haversine,
    bearing,
    point_in_polygon,
    bounding_box,
    destination_point,
)
from learning.phase_2.src.m12_geospatial.h3_grid import (
    lat_lon_to_cell,
    get_neighbors,
    compare_resolutions,
    cells_in_radius,
    RESOLUTION_EDGE_KM,
)
from learning.phase_2.src.m12_geospatial.geohash import (
    encode,
    decode,
    neighbors,
    bounding_box_geohashes,
)


class TestGeoPoint:
    def test_valid_point(self):
        p = GeoPoint(40.7484, -73.9857)
        assert p.lat == 40.7484

    def test_invalid_latitude(self):
        with pytest.raises(ValueError, match="Latitude"):
            GeoPoint(91.0, 0.0)

    def test_invalid_longitude(self):
        with pytest.raises(ValueError, match="Longitude"):
            GeoPoint(0.0, 181.0)


class TestHaversine:
    def test_zero_distance(self):
        p = GeoPoint(40.7484, -73.9857)
        assert haversine(p, p) == pytest.approx(0.0, abs=0.001)

    def test_known_distance_nyc(self):
        empire = GeoPoint(40.7484, -73.9857)
        times = GeoPoint(40.7580, -73.9855)
        dist = haversine(empire, times)
        assert 0.5 < dist < 2.0

    def test_symmetry(self):
        p1 = GeoPoint(40.7484, -73.9857)
        p2 = GeoPoint(40.7580, -73.9855)
        assert haversine(p1, p2) == pytest.approx(haversine(p2, p1), abs=0.0001)

    def test_long_distance(self):
        nyc = GeoPoint(40.7128, -74.0060)
        london = GeoPoint(51.5074, -0.1278)
        dist = haversine(nyc, london)
        assert 5500 < dist < 5700  # ~5570 km


class TestBearing:
    def test_due_north(self):
        p1 = GeoPoint(40.0, -74.0)
        p2 = GeoPoint(41.0, -74.0)
        brng = bearing(p1, p2)
        assert brng == pytest.approx(0.0, abs=1.0)

    def test_due_east(self):
        p1 = GeoPoint(0.0, 0.0)  # Equator
        p2 = GeoPoint(0.0, 1.0)
        brng = bearing(p1, p2)
        assert brng == pytest.approx(90.0, abs=1.0)


class TestPointInPolygon:
    def test_point_inside_rectangle(self):
        polygon = [
            GeoPoint(40.74, -74.00),
            GeoPoint(40.74, -73.97),
            GeoPoint(40.77, -73.97),
            GeoPoint(40.77, -74.00),
        ]
        inside = GeoPoint(40.75, -73.99)
        assert point_in_polygon(inside, polygon) is True

    def test_point_outside_rectangle(self):
        polygon = [
            GeoPoint(40.74, -74.00),
            GeoPoint(40.74, -73.97),
            GeoPoint(40.77, -73.97),
            GeoPoint(40.77, -74.00),
        ]
        outside = GeoPoint(40.80, -73.99)
        assert point_in_polygon(outside, polygon) is False

    def test_too_few_vertices(self):
        polygon = [GeoPoint(0, 0), GeoPoint(1, 1)]
        assert point_in_polygon(GeoPoint(0.5, 0.5), polygon) is False


class TestBoundingBox:
    def test_bounding_box_size(self):
        center = GeoPoint(40.7484, -73.9857)
        sw, ne = bounding_box(center, 1.0)
        assert sw.lat < center.lat < ne.lat
        assert sw.lon < center.lon < ne.lon

    def test_destination_point_distance(self):
        origin = GeoPoint(40.7484, -73.9857)
        dest = destination_point(origin, 45.0, 5.0)
        actual_dist = haversine(origin, dest)
        assert actual_dist == pytest.approx(5.0, abs=0.1)


class TestH3Grid:
    def test_cell_has_valid_id(self):
        cell = lat_lon_to_cell(40.7484, -73.9857, resolution=9)
        assert cell.cell_id.startswith("h3_09_")
        assert cell.resolution == 9

    def test_different_resolutions_different_sizes(self):
        cells = compare_resolutions(40.7484, -73.9857)
        for i in range(len(cells) - 1):
            assert cells[i].edge_length_km > cells[i + 1].edge_length_km

    def test_neighbors_count(self):
        cell = lat_lon_to_cell(40.7484, -73.9857, resolution=9)
        nbrs = get_neighbors(cell)
        assert len(nbrs) >= 4  # At least 4 unique neighbors

    def test_invalid_resolution(self):
        with pytest.raises(ValueError):
            lat_lon_to_cell(0, 0, resolution=20)


class TestGeohash:
    def test_encode_decode_roundtrip(self):
        lat, lon = 40.7484, -73.9857
        gh = encode(lat, lon, precision=9)
        bounds = decode(gh)
        assert abs(bounds.center_lat - lat) < 0.001
        assert abs(bounds.center_lon - lon) < 0.001

    def test_prefix_property(self):
        gh9 = encode(40.7484, -73.9857, precision=9)
        gh7 = encode(40.7484, -73.9857, precision=7)
        gh5 = encode(40.7484, -73.9857, precision=5)
        assert gh9.startswith(gh7)
        assert gh7.startswith(gh5)

    def test_nearby_points_share_prefix(self):
        gh1 = encode(40.7484, -73.9857, precision=5)
        gh2 = encode(40.7485, -73.9858, precision=5)  # Very close
        assert gh1 == gh2  # Same cell at precision 5

    def test_neighbors_returns_8(self):
        gh = encode(40.7484, -73.9857, precision=7)
        nbrs = neighbors(gh)
        assert len(nbrs) == 8
        assert set(nbrs.keys()) == {"n", "ne", "e", "se", "s", "sw", "w", "nw"}

    def test_invalid_precision(self):
        with pytest.raises(ValueError):
            encode(0, 0, precision=0)

    def test_decode_dimensions(self):
        bounds = decode(encode(40.7484, -73.9857, precision=7))
        assert bounds.width_km > 0
        assert bounds.height_km > 0
        # Precision 7 should be ~150m
        assert bounds.height_km < 1.0

    def test_bounding_box_geohashes(self):
        hashes = bounding_box_geohashes(40.74, -73.99, 40.76, -73.97, precision=5)
        assert len(hashes) > 0
        # All should be precision 5
        for h in hashes:
            assert len(h) == 5
