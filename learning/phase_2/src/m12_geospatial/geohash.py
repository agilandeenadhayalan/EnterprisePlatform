"""
Geohash Encoding/Decoding
============================

Geohash is a spatial indexing system that encodes a geographic location
into a short alphanumeric string. Nearby points share common prefixes.

WHY Geohash:
- Converts 2D coordinates to 1D string (easy to index in databases)
- Prefix property: "dr5ru" is inside "dr5r" which is inside "dr5"
- Simple range queries: "find all points starting with 'dr5r'"
- Fixed precision levels tied to string length

Precision levels:
    Length 1: ~5,000 km x 5,000 km
    Length 3: ~156 km x 156 km
    Length 5: ~4.9 km x 4.9 km
    Length 7: ~153 m x 153 m
    Length 9: ~4.8 m x 4.8 m
    Length 12: ~3.7 cm x 1.8 cm

TRADE-OFFS vs H3:
- [+] Simpler to implement and understand
- [+] Works with standard database indexes (prefix search)
- [-] Rectangular cells (not uniform like hexagons)
- [-] Edge effects: nearby points can have very different geohashes
       if they straddle a cell boundary
"""

from __future__ import annotations

from dataclasses import dataclass


# Base32 alphabet used by geohash
_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
_BASE32_MAP = {c: i for i, c in enumerate(_BASE32)}


@dataclass(frozen=True)
class GeohashBounds:
    """Bounding box of a geohash cell."""
    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float

    @property
    def center_lat(self) -> float:
        return (self.min_lat + self.max_lat) / 2

    @property
    def center_lon(self) -> float:
        return (self.min_lon + self.max_lon) / 2

    @property
    def width_km(self) -> float:
        """Approximate width in km."""
        import math
        lat_mid = self.center_lat
        km_per_lon = 111.32 * math.cos(math.radians(lat_mid))
        return (self.max_lon - self.min_lon) * km_per_lon

    @property
    def height_km(self) -> float:
        """Approximate height in km."""
        return (self.max_lat - self.min_lat) * 111.32


def encode(lat: float, lon: float, precision: int = 9) -> str:
    """
    Encode a lat/lon into a geohash string.

    The algorithm interleaves bits of longitude and latitude,
    then encodes them in base32. Higher precision = more characters
    = smaller cell = more accurate.

    Args:
        lat: Latitude [-90, 90]
        lon: Longitude [-180, 180]
        precision: Length of geohash string (1-12)

    Returns:
        Geohash string of specified length
    """
    if precision < 1 or precision > 12:
        raise ValueError(f"Precision must be 1-12, got {precision}")

    lat_range = [-90.0, 90.0]
    lon_range = [-180.0, 180.0]

    geohash_chars: list[str] = []
    bits = 0
    char_bits = 0
    is_lon = True  # Start with longitude

    while len(geohash_chars) < precision:
        if is_lon:
            mid = (lon_range[0] + lon_range[1]) / 2
            if lon >= mid:
                char_bits = char_bits * 2 + 1
                lon_range[0] = mid
            else:
                char_bits = char_bits * 2
                lon_range[1] = mid
        else:
            mid = (lat_range[0] + lat_range[1]) / 2
            if lat >= mid:
                char_bits = char_bits * 2 + 1
                lat_range[0] = mid
            else:
                char_bits = char_bits * 2
                lat_range[1] = mid

        is_lon = not is_lon
        bits += 1

        if bits == 5:
            geohash_chars.append(_BASE32[char_bits])
            bits = 0
            char_bits = 0

    return "".join(geohash_chars)


def decode(geohash: str) -> GeohashBounds:
    """
    Decode a geohash string to its bounding box.

    Returns the bounds of the cell, from which you can derive
    the center point and the cell dimensions.
    """
    lat_range = [-90.0, 90.0]
    lon_range = [-180.0, 180.0]
    is_lon = True

    for char in geohash:
        if char not in _BASE32_MAP:
            raise ValueError(f"Invalid geohash character: {char}")
        val = _BASE32_MAP[char]

        for bit_pos in range(4, -1, -1):
            bit = (val >> bit_pos) & 1
            if is_lon:
                mid = (lon_range[0] + lon_range[1]) / 2
                if bit == 1:
                    lon_range[0] = mid
                else:
                    lon_range[1] = mid
            else:
                mid = (lat_range[0] + lat_range[1]) / 2
                if bit == 1:
                    lat_range[0] = mid
                else:
                    lat_range[1] = mid
            is_lon = not is_lon

    return GeohashBounds(
        min_lat=lat_range[0],
        max_lat=lat_range[1],
        min_lon=lon_range[0],
        max_lon=lon_range[1],
    )


def neighbors(geohash: str) -> dict[str, str]:
    """
    Find the 8 neighboring geohash cells (N, NE, E, SE, S, SW, W, NW).

    WHY: To search an area, you need to query the target cell AND
    its neighbors (points near the boundary could be in adjacent cells).
    """
    bounds = decode(geohash)
    precision = len(geohash)

    lat_step = (bounds.max_lat - bounds.min_lat)
    lon_step = (bounds.max_lon - bounds.min_lon)

    center_lat = bounds.center_lat
    center_lon = bounds.center_lon

    directions = {
        "n":  (lat_step, 0),
        "ne": (lat_step, lon_step),
        "e":  (0, lon_step),
        "se": (-lat_step, lon_step),
        "s":  (-lat_step, 0),
        "sw": (-lat_step, -lon_step),
        "w":  (0, -lon_step),
        "nw": (lat_step, -lon_step),
    }

    result: dict[str, str] = {}
    for direction, (dlat, dlon) in directions.items():
        nlat = center_lat + dlat
        nlon = center_lon + dlon

        # Wrap around
        nlat = max(-90, min(90, nlat))
        if nlon > 180:
            nlon -= 360
        elif nlon < -180:
            nlon += 360

        result[direction] = encode(nlat, nlon, precision)

    return result


def bounding_box_geohashes(
    sw_lat: float,
    sw_lon: float,
    ne_lat: float,
    ne_lon: float,
    precision: int = 7,
) -> list[str]:
    """
    Find all geohash cells that overlap a bounding box.

    WHY: "Find all drivers in this rectangular map viewport."
    Convert the viewport to geohashes, then query the database
    for drivers whose geohash starts with any of these prefixes.
    """
    bounds = decode(encode(sw_lat, sw_lon, precision))
    lat_step = bounds.max_lat - bounds.min_lat
    lon_step = bounds.max_lon - bounds.min_lon

    if lat_step <= 0 or lon_step <= 0:
        return [encode(sw_lat, sw_lon, precision)]

    hashes: set[str] = set()

    lat = sw_lat
    while lat <= ne_lat + lat_step:
        lon = sw_lon
        while lon <= ne_lon + lon_step:
            hashes.add(encode(lat, lon, precision))
            lon += lon_step * 0.5  # Overlap to avoid gaps
        lat += lat_step * 0.5

    return sorted(hashes)
