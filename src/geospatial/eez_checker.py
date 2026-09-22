"""Real Maritime Geospatial & EEZ Boundary Checker.
Uses Shapely geometry to perform spatial point-in-polygon queries against real
UNCLOS Exclusive Economic Zone boundaries for the Indian Ocean & Arabian Sea littoral.
"""

import json
import math
import os
from typing import Dict, List, Optional, Tuple
from shapely.geometry import Point, Polygon, MultiPolygon
from src.schemas.geospatial import GeoContext
from src.utils.logger import setup_logger

logger = setup_logger("eez_checker")

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes great-circle distance between two points on Earth in kilometers."""
    R = 6371.0 # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2.0) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(R * c, 2)

class RealEEZChecker:
    """Spatial classifier for real sovereign EEZ boundaries and high-risk maritime zones."""

    # Major port centroids for proximity calculations
    PORTS = [
        {"name": "Mundra (India)", "lat": 22.75, "lon": 69.70},
        {"name": "Mumbai / JNPT (India)", "lat": 18.95, "lon": 72.95},
        {"name": "Kandla (India)", "lat": 23.00, "lon": 70.22},
        {"name": "Kochi (India)", "lat": 9.97, "lon": 76.27},
        {"name": "Sohar (Oman)", "lat": 24.50, "lon": 56.63},
        {"name": "Salalah (Oman)", "lat": 16.94, "lon": 54.00},
        {"name": "Karachi (Pakistan)", "lat": 24.80, "lon": 66.98},
    ]

    # Known STS transfer rendezvous sectors
    STS_ZONES = [
        {"name": "Fujairah Offshore Anchorage", "lat": 25.18, "lon": 56.55, "radius_km": 60.0},
        {"name": "Gulf of Oman Evasion Corridor", "lat": 24.00, "lon": 58.50, "radius_km": 120.0},
        {"name": "Arabian Sea Deepwater STS Sector", "lat": 19.50, "lon": 62.50, "radius_km": 150.0},
    ]

    # Representative coastline nodes for fast coastal distance approximation
    COASTLINE_POINTS = [
        (23.65, 68.10), (22.50, 69.00), (20.80, 70.50), (21.00, 72.50),
        (18.95, 72.80), (15.50, 73.75), (13.00, 74.80), (9.95, 76.25),
        (8.08, 77.55), (24.80, 66.95), (25.10, 62.30), (23.60, 58.50)
    ]

    def __init__(self, geojson_path: str = "data/raw/geospatial/arabian_sea_eez.geojson"):
        self.geojson_path = geojson_path
        self.zones: List[Dict] = []
        self._load_zones()

    def _load_zones(self):
        if not os.path.exists(self.geojson_path):
            logger.warning(f"EEZ GeoJSON not found at {self.geojson_path}")
            return
        with open(self.geojson_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for feat in data.get("features", []):
            props = feat.get("properties", {})
            geom = feat.get("geometry", {})
            coords = geom.get("coordinates", [])
            if geom.get("type") == "Polygon" and coords:
                poly = Polygon(coords[0])
                self.zones.append({
                    "polygon": poly,
                    "sovereign": props.get("sovereign", "International Waters"),
                    "zone_type": props.get("zone_type", ""),
                    "properties": props
                })
        logger.info(f"Loaded {len(self.zones)} real maritime zones from {self.geojson_path}")

    def compute_distance_to_coast_km(self, lat: float, lon: float) -> float:
        """Computes distance to nearest coastal node."""
        min_dist = float("inf")
        for clat, clon in self.COASTLINE_POINTS:
            d = haversine_km(lat, lon, clat, clon)
            if d < min_dist:
                min_dist = d
        return round(min_dist, 1)

    def get_geo_context(self, lat: float, lon: float) -> GeoContext:
        """
        Classifies geographic location against sovereign EEZ boundaries,
        calculates port and coast distances, and tags maritime risk zones.
        """
        pt = Point(lon, lat) # Shapely uses (x=lon, y=lat)
        inside_eez = False
        eez_sovereign = None
        risk_tags: List[str] = []

        # Point in polygon checks
        for z in self.zones:
            if z["polygon"].contains(pt):
                sovereign = z["sovereign"]
                if sovereign != "International Waters":
                    inside_eez = True
                    eez_sovereign = sovereign
                    risk_tags.append(f"INSIDE_{sovereign.upper()}_EEZ")
                else:
                    risk_tags.append("INTERNATIONAL_WATERS")
                    if "Sanctions" in z["zone_type"]:
                        risk_tags.append("KNOWN_SANCTIONS_CORRIDOR")

        # Nearest Port
        nearest_port = None
        min_port_dist = float("inf")
        for p in self.PORTS:
            d = haversine_km(lat, lon, p["lat"], p["lon"])
            if d < min_port_dist:
                min_port_dist = d
                nearest_port = p["name"]

        # Nearest STS corridor
        nearest_sts = None
        min_sts_dist = float("inf")
        for s in self.STS_ZONES:
            d = haversine_km(lat, lon, s["lat"], s["lon"])
            if d < min_sts_dist:
                min_sts_dist = d
                nearest_sts = s["name"]
                if d <= s["radius_km"]:
                    risk_tags.append(f"PROXIMITY_{s['name'].upper().replace(' ', '_')}")

        dist_coast = self.compute_distance_to_coast_km(lat, lon)
        
        # Approximate distance to EEZ boundary line
        dist_eez_border = 35.0 if inside_eez else max(15.0, dist_coast - 370.0) # ~200 nautical miles = 370.4 km
        if dist_eez_border < 0:
            dist_eez_border = abs(dist_eez_border)

        return GeoContext(
            latitude=lat,
            longitude=lon,
            inside_eez=inside_eez,
            eez_country=eez_sovereign,
            distance_to_eez_boundary_km=round(dist_eez_border, 1),
            distance_to_coast_km=dist_coast,
            nearest_port_name=nearest_port,
            distance_to_nearest_port_km=min_port_dist,
            inside_mpa=False,
            inside_rfmo=False,
            nearest_sts_zone_name=nearest_sts,
            distance_to_sts_zone_km=min_sts_dist,
            risk_zone_tags=risk_tags
        )
