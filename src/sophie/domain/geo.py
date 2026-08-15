"""Pure geospatial helpers - no I/O, no framework imports.

Used by import providers (e.g. `sophie.providers.sports_tracker`) to derive a
workout's total distance from a sequence of GPS trackpoints when the source
file does not already carry a pre-computed total distance (GPX files rarely
do; FIT session messages usually do).
"""

from __future__ import annotations

import math
from collections.abc import Sequence

_EARTH_RADIUS_M = 6_371_000.0


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon points (in decimal degrees), in meters."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * _EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(a)))


def track_distance_m(points: Sequence[tuple[float, float]]) -> float:
    """Total distance in meters along a polyline of (lat, lon) points, computed as the
    sum of haversine distances between consecutive points. Returns 0.0 for fewer than
    two points."""
    if len(points) < 2:
        return 0.0
    total = 0.0
    for (lat1, lon1), (lat2, lon2) in zip(points, points[1:], strict=False):
        total += haversine_distance_m(lat1, lon1, lat2, lon2)
    return total
