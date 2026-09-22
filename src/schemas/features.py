"""Engineered feature schemas representing Pillar 1 of the project evaluation.
Contains explicit, mathematically defined features across SAR, AIS, Geospatial,
Historical, and SAR-AIS Fusion domains.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class SARFeatures(BaseModel):
    length_m: float = Field(..., ge=0.0, description="Estimated target length in meters")
    width_m: float = Field(..., ge=0.0, description="Estimated target beam in meters")
    aspect_ratio: float = Field(..., ge=0.0, description="Ratio of length to beam (L/B)")
    detection_area_m2: float = Field(..., ge=0.0, description="Target pixel area converted to square meters")
    orientation_deg: Optional[float] = Field(None, ge=0.0, le=360.0, description="Major axis orientation in degrees")
    
    # Radiometric and Clutter Contrast
    peak_backscatter_db: Optional[float] = Field(None, description="Maximum sigma-nought intensity inside target mask")
    mean_backscatter_db: Optional[float] = Field(None, description="Mean sigma-nought intensity inside target mask")
    background_clutter_db: Optional[float] = Field(None, description="Estimated background clutter sigma-nought")
    target_to_clutter_ratio_db: Optional[float] = Field(None, description="Target contrast over background clutter")
    backscatter_variance: Optional[float] = Field(None, ge=0.0, description="Variance of pixel values across the ship target")
    
    # Structural Descriptors
    compactness: Optional[float] = Field(None, ge=0.0, description="Perimeter^2 / (4 * pi * Area)")
    eccentricity: Optional[float] = Field(None, ge=0.0, le=1.0, description="Second moment ellipse eccentricity")
    incidence_angle_deg: Optional[float] = Field(None, ge=0.0, le=90.0, description="Radar incidence angle")
    polarization_ratio: Optional[float] = Field(None, description="VH / VV backscatter ratio if dual-pol available")

class AISFeatures(BaseModel):
    mean_speed_knots: float = Field(..., ge=0.0, description="Mean Speed Over Ground across track window")
    speed_variance: float = Field(..., ge=0.0, description="Variance of SOG across track window")
    max_speed_knots: float = Field(..., ge=0.0, description="Maximum recorded SOG")
    speed_acceleration_kph2: Optional[float] = Field(None, description="Rate of speed change (acceleration/deceleration)")
    heading_variance: float = Field(..., ge=0.0, description="Circular variance of vessel heading/course")
    mean_turn_rate_deg_min: Optional[float] = Field(None, ge=0.0, description="Rate of course change per minute")
    trajectory_curvature: Optional[float] = Field(None, ge=0.0, description="Ratio of actual path length to endpoint displacement")
    total_distance_km: float = Field(..., ge=0.0, description="Total distance travelled along observed AIS track")
    
    # Temporal and Transmission Gap Features
    ais_gap_count_30d: int = Field(default=0, ge=0, description="Total number of AIS transmission outages in past 30 days")
    longest_ais_gap_hours: float = Field(default=0.0, ge=0.0, description="Maximum continuous AIS outage duration")
    mean_ais_gap_hours: float = Field(default=0.0, ge=0.0, description="Average duration of AIS outages")
    current_gap_duration_hours: float = Field(default=0.0, ge=0.0, description="Elapsed time since last valid AIS broadcast")
    loitering_duration_hours: float = Field(default=0.0, ge=0.0, description="Duration spent drifting at speed < 3 knots")

class GeospatialFeatures(BaseModel):
    distance_to_shore_km: float = Field(..., ge=0.0, description="Straight-line distance to closest land boundary")
    distance_to_nearest_port_km: float = Field(..., ge=0.0, description="Distance to closest recognized commercial port")
    distance_to_eez_boundary_km: float = Field(..., ge=0.0, description="Distance to nearest national Exclusive Economic Zone boundary")
    is_inside_eez: bool = Field(..., description="Binary indicator: located inside sovereign EEZ")
    is_inside_mpa_or_rfmo: bool = Field(default=False, description="Binary indicator: located in protected marine area")
    proximity_to_sts_corridor_km: Optional[float] = Field(None, ge=0.0, description="Distance to designated ship-to-ship transfer zone")
    proximity_to_nearest_vessel_km: Optional[float] = Field(None, ge=0.0, description="Distance to nearest concurrent vessel in area")
    vessel_density_local_km2: Optional[float] = Field(None, ge=0.0, description="Local vessel traffic density in 25km radius")

class HistoricalFeatures(BaseModel):
    prior_sanctions_involvement: bool = Field(default=False, description="Flagged in historical maritime illicit trade reports")
    flag_change_count_12m: int = Field(default=0, ge=0, description="Number of flag changes in past 12 months (Flag hopping indicator)")
    name_change_count_24m: int = Field(default=0, ge=0, description="Number of vessel name changes in past 24 months")
    historical_loitering_events_6m: int = Field(default=0, ge=0, description="Count of past suspicious slow-speed drift events")
    historical_sts_encounters_6m: int = Field(default=0, ge=0, description="Count of past rendezvous within 500m of another tanker")
    route_anomaly_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Deviation score against historical traffic lanes")

class FusionFeatures(BaseModel):
    """Features quantifying the correlation (or discrepancy) between SAR detection and candidate AIS track."""
    spatial_discrepancy_km: float = Field(..., ge=0.0, description="Distance between SAR target position and extrapolated AIS position")
    temporal_difference_minutes: float = Field(..., ge=0.0, description="Time delta between SAR acquisition and closest AIS broadcast")
    dimension_mismatch_ratio: Optional[float] = Field(None, ge=0.0, description="|SAR_length - AIS_length| / AIS_length")
    heading_discrepancy_deg: Optional[float] = Field(None, ge=0.0, le=180.0, description="Angular difference between SAR orientation and AIS COG")
    speed_consistency_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Consistency of SAR Doppler/wake speed vs AIS SOG")
    predicted_ais_position_error_km: Optional[float] = Field(None, ge=0.0, description="Extrapolation uncertainty radius from AIS dead-reckoning")
    is_spatially_correlated: bool = Field(..., description="Binary: whether SAR target is explained by a known AIS vessel")
    candidate_identity_score: float = Field(..., ge=0.0, le=1.0, description="Composite correlation score across all dimensions")

class EngineeredFeatures(BaseModel):
    """Composite container unifying all engineered feature domains for downstream ML and LLM ingestion."""
    detection_id: str = Field(..., description="Unique SAR detection identifier")
    mmsi_candidate: Optional[str] = Field(None, description="MMSI of matched AIS vessel or candidate, if any")
    timestamp: str = Field(..., description="UTC timestamp of the observation")
    
    # Feature Modules
    sar: SARFeatures
    ais: Optional[AISFeatures] = None
    geospatial: GeospatialFeatures
    historical: HistoricalFeatures
    fusion: FusionFeatures
    
    def to_flat_dict(self) -> Dict[str, float]:
        """Flattens numerical features into a clean dictionary for ML model training and feature importance."""
        flat = {}
        for prefix, module in [
            ("sar", self.sar),
            ("ais", self.ais),
            ("geo", self.geospatial),
            ("hist", self.historical),
            ("fusion", self.fusion),
        ]:
            if module is not None:
                for k, v in module.model_dump().items():
                    if isinstance(v, (int, float)) and not isinstance(v, bool):
                        flat[f"{prefix}_{k}"] = float(v)
                    elif isinstance(v, bool):
                        flat[f"{prefix}_{k}"] = 1.0 if v else 0.0
        return flat
