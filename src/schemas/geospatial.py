from typing import List, Optional
from pydantic import BaseModel, Field

class GeoContext(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    
    # Territorial and EEZ parameters
    inside_eez: bool = Field(..., description="Whether location is inside an Exclusive Economic Zone")
    eez_country: Optional[str] = Field(None, description="Sovereign state of the EEZ (e.g. India, Oman)")
    distance_to_eez_boundary_km: float = Field(..., ge=0.0, description="Distance to closest EEZ border")
    distance_to_coast_km: float = Field(..., ge=0.0, description="Straight-line distance to nearest coastline")
    
    # Infrastructure and maritime hubs
    nearest_port_name: Optional[str] = Field(None, description="Name of closest commercial or fishing port")
    distance_to_nearest_port_km: Optional[float] = Field(None, ge=0.0)
    
    # Maritime Risk and Activity Zones
    inside_mpa: bool = Field(default=False, description="Inside a Marine Protected Area")
    inside_rfmo: bool = Field(default=False, description="Inside a Regional Fisheries Management Organization boundary")
    nearest_sts_zone_name: Optional[str] = Field(None, description="Nearest known Ship-to-Ship transfer corridor")
    distance_to_sts_zone_km: Optional[float] = Field(None, ge=0.0)
    risk_zone_tags: List[str] = Field(default_factory=list, description="Descriptive tags (e.g. ['SANCTIONS_CORRIDOR', 'HIGH_TRAFFIC'])")
