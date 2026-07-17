"""Geolocation utility functions."""

import math
from typing import Optional

try:
    from geopy.distance import geodesic
except ImportError:
    geodesic = None


def calculate_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float
) -> float:
    """
    Calculate the geodesic distance (in kilometers) between two coordinates.
    """
    if None in (lat1, lon1, lat2, lon2):
        return 0.0

    if geodesic:
        try:
            return geodesic((lat1, lon1), (lat2, lon2)).km
        except Exception:
            pass

    # Fallback to Haversine formula
    R = 6371.0  # Earth's radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c
