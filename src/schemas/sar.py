from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class SARDetection(BaseModel):
    detection_id: str = Field(..., description="Unique SAR detection identifier")
    scene_id: str = Field(..., description="Sentinel-1 or SAR product ID (e.g. S1A_IW_GRDH...)")
    timestamp: datetime = Field(..., description="Acquisition UTC timestamp of the SAR scene")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Center latitude of detection")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Center longitude of detection")
    
    # Physical/Morphological measurements
    length_m: float = Field(..., ge=0.0, description="Estimated vessel length in meters")
    width_m: float = Field(..., ge=0.0, description="Estimated vessel beam/width in meters")
    aspect_ratio: float = Field(..., ge=0.0, description="Ratio of length to width")
    heading_deg: Optional[float] = Field(None, ge=0.0, le=360.0, description="Estimated vessel orientation in degrees")
    area_m2: Optional[float] = Field(None, ge=0.0, description="Effective target radar footprint area in square meters")
    
    # Radiometric features
    peak_backscatter_db: Optional[float] = Field(None, description="Peak radar backscatter intensity (dB)")
    mean_backscatter_db: Optional[float] = Field(None, description="Mean target backscatter (dB)")
    background_mean_db: Optional[float] = Field(None, description="Local sea clutter mean intensity (dB)")
    target_clutter_ratio_db: Optional[float] = Field(None, description="Contrast: target backscatter minus sea clutter (dB)")
    
    # Sensor metadata
    sensor: str = Field(default="SENTINEL-1", description="SAR sensor platform")
    polarization: str = Field(default="VV", description="Polarization channel (VV, VH, HH, HV)")
    incidence_angle_deg: Optional[float] = Field(None, ge=0.0, le=90.0, description="Radar incidence angle at detection point")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detector confidence score")
    bbox_pixel: Optional[List[int]] = Field(None, description="Bounding box in chip pixel coordinates [xmin, ymin, xmax, ymax]")

class SARScene(BaseModel):
    scene_id: str = Field(..., description="SAR scene product name")
    acquisition_time: datetime = Field(..., description="Scene acquisition time")
    sensor: str = Field(default="Sentinel-1", description="Satellite name")
    polarizations: List[str] = Field(default_factory=lambda: ["VV", "VH"])
    orbit_direction: str = Field(default="ASCENDING", description="ASCENDING or DESCENDING")
    footprint_wkt: Optional[str] = Field(None, description="Well-Known Text geometry of the scene footprint")
    detections: List[SARDetection] = Field(default_factory=list, description="Extracted detections within this scene")
