"""Pillar 1: SAR-AIS Fusion Feature Engineering Module.
Computes multi-dimensional spatial, temporal, physical, and kinematic correlation
metrics between SAR radar detections and AIS broadcasts.
"""

import math
from typing import Optional
from src.schemas.sar import SARDetection
from src.schemas.ais import AISObservation
from src.schemas.features import FusionFeatures
from src.geospatial.eez_checker import haversine_km

def compute_heading_discrepancy(heading_sar: Optional[float], cog_ais: Optional[float]) -> Optional[float]:
    """
    Computes angular difference between SAR radar orientation and AIS Course Over Ground.
    Since SAR vessel orientation has 180-degree ambiguity (bow vs stern without wake),
    the minimal difference is computed modulo 180 degrees.
    """
    if heading_sar is None or cog_ais is None:
        return None
    diff = abs(heading_sar - cog_ais) % 360.0
    # Radar 180-degree ambiguity fold
    if diff > 180.0:
        diff = 360.0 - diff
    if diff > 90.0:
        diff = 180.0 - diff
    return round(diff, 1)

def extract_fusion_features(
    sar_detection: SARDetection,
    ais_observation: Optional[AISObservation] = None,
    registered_length_m: Optional[float] = None,
    spatial_threshold_km: float = 5.0,
    temporal_threshold_minutes: float = 30.0
) -> FusionFeatures:
    """
    Evaluates spatial-temporal, physical, and kinematic correlation between a SAR target and candidate AIS track.
    If no candidate AIS observation exists, returns maximal discrepancy metrics.
    """
    if ais_observation is None:
        return FusionFeatures(
            spatial_discrepancy_km=999.0,
            temporal_difference_minutes=9999.0,
            dimension_mismatch_ratio=None,
            heading_discrepancy_deg=None,
            speed_consistency_score=0.0,
            predicted_ais_position_error_km=None,
            is_spatially_correlated=False,
            candidate_identity_score=0.0
        )

    # 1. Spatial discrepancy
    dist_km = haversine_km(
        sar_detection.latitude, sar_detection.longitude,
        ais_observation.latitude, ais_observation.longitude
    )

    # 2. Temporal discrepancy
    dt_seconds = abs((sar_detection.timestamp - ais_observation.timestamp).total_seconds())
    dt_minutes = round(dt_seconds / 60.0, 1)

    # 3. Dimension mismatch ratio
    dim_mismatch = None
    if registered_length_m and registered_length_m > 0:
        dim_mismatch = round(abs(sar_detection.length_m - registered_length_m) / registered_length_m, 3)

    # 4. Heading discrepancy
    ais_course = ais_observation.cog if (ais_observation.cog and ais_observation.cog < 360) else ais_observation.heading
    heading_diff = compute_heading_discrepancy(sar_detection.heading_deg, ais_course)

    # 5. Dead-reckoning error approximation
    # Assumes 1 knot GPS drift + velocity uncertainty over elapsed time
    speed_knots = ais_observation.sog
    dead_reckon_err_km = round((speed_knots * 1.852) * (dt_minutes / 60.0) * 0.15 + 0.5, 2)

    # 6. Composite Correlation Decision
    # Spatially correlated if distance is within tolerance plus dead reckoning buffer
    is_correlated = (dist_km <= (spatial_threshold_km + dead_reckon_err_km)) and (dt_minutes <= temporal_threshold_minutes)

    # Composite Identity Score (0.0 to 1.0)
    score = 0.0
    if is_correlated:
        # Spatial factor (1.0 at 0km, degrades to 0.0 at threshold)
        spatial_factor = max(0.0, 1.0 - (dist_km / (spatial_threshold_km + dead_reckon_err_km)))
        # Temporal factor
        temporal_factor = max(0.0, 1.0 - (dt_minutes / temporal_threshold_minutes))
        # Dimension factor
        dim_factor = max(0.0, 1.0 - (dim_mismatch or 0.2))
        score = round(0.5 * spatial_factor + 0.3 * temporal_factor + 0.2 * dim_factor, 3)

    return FusionFeatures(
        spatial_discrepancy_km=dist_km,
        temporal_difference_minutes=dt_minutes,
        dimension_mismatch_ratio=dim_mismatch,
        heading_discrepancy_deg=heading_diff,
        speed_consistency_score=round(max(0.0, 1.0 - (dist_km / 20.0)), 2),
        predicted_ais_position_error_km=dead_reckon_err_km,
        is_spatially_correlated=is_correlated,
        candidate_identity_score=score
    )
