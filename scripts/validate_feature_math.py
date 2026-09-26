"""
Automated validation script for Phase 4: Feature Engineering Math & Edge Cases.
Tests all five feature domains against edge cases, extreme inputs, coordinate limits, and stability.
"""

import math
from datetime import datetime, timezone, timedelta
import numpy as np

from src.schemas.sar import SARDetection
from src.schemas.ais import AISObservation, AISGap
from src.schemas.geospatial import GeoContext
from src.features.sar_features import extract_sar_features
from src.features.ais_features import extract_ais_features
from src.features.geospatial_features import extract_geospatial_features
from src.features.fusion_features import extract_fusion_features
from src.features.pipeline import FeaturePipeline
from src.geospatial.eez_checker import haversine_km

def run_feature_math_audit():
    results = {}
    
    # 1. Base normal objects
    sar_base = SARDetection(
        detection_id="SAR-BASE-001",
        scene_id="S1A_IW_GRDH_1SDV_20260901_TEST",
        timestamp=datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc),
        latitude=20.0,
        longitude=65.0,
        length_m=120.0,
        width_m=20.0,
        aspect_ratio=6.0,
        confidence=0.95,
        heading_deg=90.0,
        mean_backscatter_db=25.0,
        background_mean_db=7.0,
        target_clutter_ratio_db=18.0
    )
    
    geo_normal = GeoContext(
        latitude=20.0,
        longitude=65.0,
        inside_eez=False,
        eez_country=None,
        distance_to_eez_boundary_km=145.0,
        distance_to_coast_km=450.0,
        nearest_port_name="Karachi",
        distance_to_nearest_port_km=520.0,
        nearest_sts_zone_name="Arabian Sea Deepwater STS Sector",
        distance_to_sts_zone_km=65.0
    )
    
    ais_obs_normal = AISObservation(
        mmsi="123456789",
        latitude=20.01,
        longitude=65.01,
        sog=12.0,
        cog=90.0,
        heading=90.0,
        timestamp=datetime(2026, 9, 1, 11, 55, 0, tzinfo=timezone.utc)
    )
    
    # Test 1: Determinism & Repeated Execution
    f1 = FeaturePipeline.extract(sar_base, geo_normal, ais_obs_normal)
    f2 = FeaturePipeline.extract(sar_base, geo_normal, ais_obs_normal)
    vec1 = f1.to_flat_dict()
    vec2 = f2.to_flat_dict()
    results["determinism_exact_match"] = (vec1 == vec2)
    results["total_flattened_features"] = len(vec1)
    
    # Test 2: Missing AIS (None)
    f_missing_ais = FeaturePipeline.extract(sar_base, geo_normal, candidate_ais=None)
    results["missing_ais_spatial_discrepancy"] = f_missing_ais.fusion.spatial_discrepancy_km
    results["missing_ais_temporal_difference"] = f_missing_ais.fusion.temporal_difference_minutes
    results["missing_ais_is_correlated"] = f_missing_ais.fusion.is_spatially_correlated
    results["missing_ais_gap_hours"] = f_missing_ais.ais.current_gap_duration_hours
    results["missing_ais_sog_mean"] = f_missing_ais.ais.mean_speed_knots
    
    # Test 3: Zero Speed & Zero Heading Variance
    obs_zero_speed = [
        AISObservation(
            mmsi="111111111",
            latitude=20.0, longitude=65.0,
            sog=0.0, cog=0.0, heading=0.0,
            timestamp=datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc) + timedelta(minutes=10*i)
        ) for i in range(5)
    ]
    f_stationary = extract_ais_features(obs_zero_speed)
    results["stationary_sog_mean"] = f_stationary.mean_speed_knots
    results["stationary_sog_variance"] = f_stationary.speed_variance
    results["stationary_heading_variance"] = f_stationary.heading_variance
    results["stationary_curvature"] = f_stationary.trajectory_curvature
    
    # Test 4: Length Edge Cases (<30m small craft, >100m, exactly 30m, exactly 100m)
    for length in [15.0, 30.0, 99.9, 100.0, 350.0]:
        sar_l = SARDetection(
            detection_id=f"SAR-L-{int(length)}",
            scene_id="SCENE-L",
            timestamp=datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc),
            latitude=20.0, longitude=65.0,
            length_m=length, width_m=10.0,
            aspect_ratio=length / 10.0,
            confidence=0.9,
            target_clutter_ratio_db=15.0
        )
        f_l = extract_sar_features(sar_l)
        results[f"sar_length_{int(length)}m_aspect_ratio"] = f_l.aspect_ratio
        results[f"sar_length_{int(length)}m_area"] = f_l.detection_area_m2
        results[f"sar_length_{int(length)}m_compactness"] = f_l.compactness
        results[f"sar_length_{int(length)}m_eccentricity"] = f_l.eccentricity
        
    # Test 5: Coordinates near Antimeridian (179.95 E to -179.95 W)
    sar_anti = SARDetection(
        detection_id="SAR-ANTI-001",
        scene_id="SCENE-ANTI",
        timestamp=datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc),
        latitude=10.0,
        longitude=179.95,
        length_m=100.0,
        width_m=20.0,
        aspect_ratio=5.0,
        confidence=0.9
    )
    ais_anti = AISObservation(
        mmsi="222222222",
        timestamp=datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc),
        latitude=10.0,
        longitude=-179.95,
        sog=10.0,
        cog=90.0
    )
    f_anti = extract_fusion_features(sar_anti, ais_anti)
    results["antimeridian_spatial_discrepancy_km"] = f_anti.spatial_discrepancy_km
    results["antimeridian_is_correlated"] = f_anti.is_spatially_correlated
    
    # Test 6: Coordinates near the Poles (+89.0 deg Lat)
    sar_polar = SARDetection(
        detection_id="SAR-POLAR-001",
        scene_id="SCENE-POLAR",
        timestamp=datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc),
        latitude=89.0,
        longitude=0.0,
        length_m=100.0,
        width_m=20.0,
        aspect_ratio=5.0,
        confidence=0.9
    )
    ais_polar = AISObservation(
        mmsi="333333333",
        timestamp=datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc),
        latitude=89.01,
        longitude=0.0,
        sog=5.0,
        cog=0.0
    )
    f_polar = extract_fusion_features(sar_polar, ais_polar)
    results["polar_spatial_discrepancy_km"] = f_polar.spatial_discrepancy_km
    
    # Test 7: Numerical Stability with zero width
    sar_zero_w = SARDetection(
        detection_id="SAR-ZERO-W",
        scene_id="SCENE-ZERO",
        timestamp=datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc),
        latitude=20.0, longitude=65.0,
        length_m=100.0, width_m=0.0,
        aspect_ratio=0.0,
        confidence=0.9
    )
    f_zw = extract_sar_features(sar_zero_w)
    results["zero_width_aspect_ratio"] = f_zw.aspect_ratio
    results["zero_width_eccentricity"] = f_zw.eccentricity
    results["zero_width_compactness"] = f_zw.compactness
        
    # Test 8: Extremely long AIS gap (e.g. 504 hours / 21 days)
    gap_long = AISGap(
        mmsi="444444444",
        gap_start=datetime(2026, 8, 11, 12, 0, 0, tzinfo=timezone.utc),
        gap_end=datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc),
        duration_hours=504.0,
        start_lat=20.0, start_lon=65.0, end_lat=20.0, end_lon=65.0
    )
    f_long_gap = extract_ais_features(observations=[], gaps=[gap_long])
    results["long_gap_hours"] = f_long_gap.current_gap_duration_hours
    results["long_gap_count"] = f_long_gap.ais_gap_count_30d
    
    # Test 9: Future information check & label leakage
    flat_keys = list(vec1.keys())
    results["has_future_leakage"] = any("future" in k or "forecast" in k for k in flat_keys)
    results["has_target_label_leakage"] = any(k in ["is_dark", "deliberate_dark", "risk_score", "threat_tier", "is_sanctioned"] for k in flat_keys)
    
    print("=== FEATURE MATH & EDGE CASE AUDIT RESULTS ===")
    for k, v in results.items():
        print(f"  {k}: {v}")
    return results

if __name__ == "__main__":
    run_feature_math_audit()
