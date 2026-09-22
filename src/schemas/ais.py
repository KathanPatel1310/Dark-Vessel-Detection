from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class AISObservation(BaseModel):
    mmsi: str = Field(..., description="Maritime Mobile Service Identity (9-digit string)")
    imo: Optional[str] = Field(None, description="International Maritime Organization number (7-digit string)")
    vessel_name: Optional[str] = Field(None, description="Vessel broadcast name")
    callsign: Optional[str] = Field(None, description="Radio callsign")
    ship_type: Optional[str] = Field(None, description="AIS ship type code or classification (e.g. Tanker, Cargo, Fishing)")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Broadcast latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Broadcast longitude")
    sog: float = Field(..., ge=0.0, le=100.0, description="Speed Over Ground in knots")
    cog: float = Field(..., ge=0.0, le=360.0, description="Course Over Ground in degrees")
    heading: Optional[float] = Field(None, ge=0.0, le=360.0, description="True heading in degrees (511 indicates not available)")
    draught_m: Optional[float] = Field(None, ge=0.0, description="Vessel draught in meters")
    destination: Optional[str] = Field(None, description="Reported destination port")
    eta: Optional[datetime] = Field(None, description="Estimated Time of Arrival")
    timestamp: datetime = Field(..., description="Observation UTC timestamp")
    flag_country: Optional[str] = Field(None, description="Country of registry flag")

class AISGap(BaseModel):
    mmsi: str = Field(..., description="MMSI of the vessel experiencing the transmission gap")
    gap_start: datetime = Field(..., description="Timestamp of the last AIS broadcast before darkness")
    gap_end: Optional[datetime] = Field(None, description="Timestamp of first AIS broadcast upon reappearance")
    duration_hours: float = Field(..., ge=0.0, description="Duration of AIS silence in hours")
    start_lat: float = Field(..., ge=-90.0, le=90.0)
    start_lon: float = Field(..., ge=-180.0, le=180.0)
    end_lat: Optional[float] = Field(None, ge=-90.0, le=90.0)
    end_lon: Optional[float] = Field(None, ge=-180.0, le=180.0)
    distance_covered_km: Optional[float] = Field(None, ge=0.0, description="Displacement during the dark period")
    implied_speed_knots: Optional[float] = Field(None, ge=0.0, description="Implied average speed between endpoints")
    is_suspicious: bool = Field(default=False, description="Flagged as suspicious based on location and duration")
    justification: Optional[str] = Field(None, description="Reasoning for suspicion or benign explanation (e.g. low satellite coverage)")
