"""Pillar 1: Geospatial Feature Engineering Module.
Transforms geographic context, territorial boundaries, and port/corridor proximity into normalized spatial features.
"""

from typing import List, Optional
from src.schemas.geospatial import GeoContext
from src.schemas.features import GeospatialFeatures

def extract_geospatial_features(
    geo_context: GeoContext,
    proximity_to_nearest_vessel_km: Optional[float] = None,
    vessel_density_local_km2: Optional[float] = None
) -> GeospatialFeatures:
    """
    Extracts explicit, deterministic spatial features from a GeoContext object.
    """
    return GeospatialFeatures(
        distance_to_shore_km=geo_context.distance_to_coast_km,
        distance_to_nearest_port_km=geo_context.distance_to_nearest_port_km or 999.0,
        distance_to_eez_boundary_km=geo_context.distance_to_eez_boundary_km,
        is_inside_eez=geo_context.inside_eez,
        is_inside_mpa_or_rfmo=geo_context.inside_mpa or geo_context.inside_rfmo,
        proximity_to_sts_corridor_km=geo_context.distance_to_sts_zone_km,
        proximity_to_nearest_vessel_km=proximity_to_nearest_vessel_km,
        vessel_density_local_km2=vessel_density_local_km2
    )
