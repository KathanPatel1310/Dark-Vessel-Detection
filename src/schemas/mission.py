from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field

class BoundingBox(BaseModel):
    min_lat: float = Field(..., ge=-90.0, le=90.0, description="Southernmost latitude")
    max_lat: float = Field(..., ge=-90.0, le=90.0, description="Northernmost latitude")
    min_lon: float = Field(..., ge=-180.0, le=180.0, description="Westernmost longitude")
    max_lon: float = Field(..., ge=-180.0, le=180.0, description="Easternmost longitude")

class Mission(BaseModel):
    mission_id: str = Field(..., description="Unique alphanumeric identifier for the investigation mission")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Mission initialization UTC timestamp")
    time_window_start: datetime = Field(..., description="Start of satellite pass and AIS correlation window")
    time_window_end: datetime = Field(..., description="End of correlation window")
    roi_name: str = Field(default="Arabian Sea", description="Name of the maritime area of interest")
    bbox: BoundingBox = Field(..., description="Geographic bounding box for the mission")
    priority: str = Field(default="MEDIUM", description="Mission priority: LOW, MEDIUM, HIGH, CRITICAL")
    trigger_source: str = Field(default="MANUAL_QUERY", description="Trigger: MANUAL_QUERY, SAR_PASS_ALERT, ANOMALY_TRIGGER")
    notes: Optional[str] = None
