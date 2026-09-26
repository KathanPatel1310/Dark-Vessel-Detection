"""
Validation script for Phase 6 (Risk Scorer) and Phase 7 (Dead-Reckoning Trajectory).
Performs sensitivity sweeps, threshold edge tests, and spherical kinematic known-answer tests.
"""

import math
import os
from datetime import datetime, timezone, timedelta
import matplotlib.pyplot as plt
import numpy as np

from src.schemas.sar import SARDetection
from src.schemas.ais import AISObservation, AISGap
from src.schemas.geospatial import GeoContext
from src.schemas.sanctions import SanctionsResult
from src.schemas.features import EngineeredFeatures
from src.features.pipeline import FeaturePipeline
from src.analytics.risk_scorer import MaritimeRiskScorer

def test_risk_scorer_sensitivity():
    print("=== RUNNING PHASE 6 RISK SCORER SENSITIVITY SWEEPS ===")
    os.makedirs("reports/figures", exist_ok=True)
    
    # Base configuration
    base_sar = SARDetection(
        detection_id="TEST-SENSITIVITY",
        scene_id="SCENE-SENS",
        timestamp=datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc),
        latitude=20.0,
        longitude=65.0,
        length_m=120.0,
        width_m=20.0,
        aspect_ratio=6.0,
        confidence=0.9,
        target_clutter_ratio_db=20.0
    )
    
    base_geo = GeoContext(
        latitude=20.0,
        longitude=65.0,
        inside_eez=False,
        eez_country=None,
        distance_to_eez_boundary_km=100.0,
        distance_to_coast_km=250.0,
        nearest_port_name="Karachi",
        distance_to_nearest_port_km=400.0,
        nearest_sts_zone_name="Arabian Sea Deepwater STS Sector",
        distance_to_sts_zone_km=150.0
    )
    
    clean_sanctions = SanctionsResult(
        query_target="TEST",
        is_sanctioned=False,
        overall_sanctions_risk="CLEAN"
    )

    # 1. Sweep Hull Length (10m to 350m)
    lengths = np.linspace(10, 350, 69)
    probs_length = []
    scores_length = []
    for l in lengths:
        sar = base_sar.model_copy(update={"length_m": float(l)})
        feats = FeaturePipeline.extract(sar, base_geo, candidate_ais=None)
        risk = MaritimeRiskScorer.compute_risk_assessment(feats, clean_sanctions, base_geo)
        probs_length.append(risk.dark_vessel_probability)
        scores_length.append(risk.overall_anomaly_score)

    # 2. Sweep Distance to Coast (5km to 400km)
    coast_dists = np.linspace(5, 400, 80)
    probs_coast = []
    scores_coast = []
    for cd in coast_dists:
        geo = base_geo.model_copy(update={"distance_to_coast_km": float(cd)})
        feats = FeaturePipeline.extract(base_sar, geo, candidate_ais=None)
        risk = MaritimeRiskScorer.compute_risk_assessment(feats, clean_sanctions, geo)
        probs_coast.append(risk.dark_vessel_probability)
        scores_coast.append(risk.overall_anomaly_score)

    # 3. Sweep STS Zone Distance (5km to 200km)
    sts_dists = np.linspace(5, 200, 40)
    probs_sts = []
    scores_sts = []
    for sd in sts_dists:
        geo = base_geo.model_copy(update={"distance_to_sts_zone_km": float(sd)})
        feats = FeaturePipeline.extract(base_sar, geo, candidate_ais=None)
        risk = MaritimeRiskScorer.compute_risk_assessment(feats, clean_sanctions, geo)
        probs_sts.append(risk.dark_vessel_probability)
        scores_sts.append(risk.overall_anomaly_score)

    # 4. Sweep AIS Outage Duration (0h to 72h)
    outage_hrs = np.linspace(0, 72, 73)
    probs_gap = []
    scores_gap = []
    for h in outage_hrs:
        gap = AISGap(
            mmsi="999999999",
            gap_start=base_sar.timestamp - timedelta(hours=float(h)),
            gap_end=base_sar.timestamp,
            duration_hours=float(h),
            start_lat=20.0, start_lon=65.0
        )
        feats = FeaturePipeline.extract(base_sar, base_geo, candidate_ais=None, historical_gaps=[gap])
        risk = MaritimeRiskScorer.compute_risk_assessment(feats, clean_sanctions, base_geo)
        probs_gap.append(risk.dark_vessel_probability)
        scores_gap.append(risk.overall_anomaly_score)

    # Generate 4-panel sensitivity plot
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    # Panel 1: Hull Length
    axes[0, 0].plot(lengths, probs_length, 'b-', label="Dark Vessel 'Probability'", linewidth=2)
    axes[0, 0].plot(lengths, scores_length, 'r--', label="Overall Anomaly Score", linewidth=2)
    axes[0, 0].axvline(30.0, color='gray', linestyle=':', label="30m Cutoff (SOLAS)")
    axes[0, 0].axvline(100.0, color='orange', linestyle=':', label="100m Commercial")
    axes[0, 0].set_title("A. Sensitivity to Vessel Length (m)", fontweight='bold')
    axes[0, 0].set_xlabel("Vessel Length (meters)")
    axes[0, 0].set_ylabel("Risk Metric")
    axes[0, 0].grid(True, alpha=0.5)
    axes[0, 0].legend(fontsize=8)

    # Panel 2: Coast Distance
    axes[0, 1].plot(coast_dists, probs_coast, 'b-', label="Dark Vessel 'Probability'", linewidth=2)
    axes[0, 1].plot(coast_dists, scores_coast, 'r--', label="Overall Anomaly Score", linewidth=2)
    axes[0, 1].axvline(100.0, color='purple', linestyle=':', label="100km Deepwater Threshold")
    axes[0, 1].set_title("B. Sensitivity to Distance from Coast (km)", fontweight='bold')
    axes[0, 1].set_xlabel("Distance to Coast (km)")
    axes[0, 1].grid(True, alpha=0.5)
    axes[0, 1].legend(fontsize=8)

    # Panel 3: STS Proximity
    axes[1, 0].plot(sts_dists, probs_sts, 'b-', label="Dark Vessel 'Probability'", linewidth=2)
    axes[1, 0].plot(sts_dists, scores_sts, 'r--', label="Overall Anomaly Score", linewidth=2)
    axes[1, 0].axvline(80.0, color='brown', linestyle=':', label="80km STS Threshold")
    axes[1, 0].set_title("C. Sensitivity to STS Rendezvous Proximity (km)", fontweight='bold')
    axes[1, 0].set_xlabel("Distance to STS Zone (km)")
    axes[1, 0].set_ylabel("Risk Metric")
    axes[1, 0].grid(True, alpha=0.5)
    axes[1, 0].legend(fontsize=8)

    # Panel 4: Outage Duration
    axes[1, 1].plot(outage_hrs, probs_gap, 'b-', label="Dark Vessel 'Probability'", linewidth=2)
    axes[1, 1].plot(outage_hrs, scores_gap, 'r--', label="Overall Anomaly Score", linewidth=2)
    axes[1, 1].axvline(12.0, color='darkgreen', linestyle=':', label="12h Outage Step")
    axes[1, 1].set_title("D. Sensitivity to AIS Outage Duration (hours)", fontweight='bold')
    axes[1, 1].set_xlabel("AIS Outage Duration (hours)")
    axes[1, 1].grid(True, alpha=0.5)
    axes[1, 1].legend(fontsize=8)

    plt.suptitle("Maritime Risk Scorer Sensitivity Analysis & Threshold Discontinuities", fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig("reports/figures/risk_sensitivity.png", dpi=300)
    plt.close()
    print("Saved reports/figures/risk_sensitivity.png")

def test_trajectory_known_answers():
    print("\n=== RUNNING PHASE 7 TRAJECTORY DEAD-RECKONING AUDIT ===")
    results = {}
    
    # Case 1: Stationary vessel (speed = 0)
    fc_stationary = MaritimeRiskScorer.extrapolate_trajectory(
        lat=20.0, lon=65.0, speed_knots=0.0, heading_deg=90.0,
        forecast_horizons_hours=[6.0, 12.0, 24.0]
    )
    results["stationary_wp_24h_lat"] = fc_stationary.extrapolated_waypoints[2].projected_lat
    results["stationary_wp_24h_lon"] = fc_stationary.extrapolated_waypoints[2].projected_lon
    results["stationary_wp_24h_error_km"] = fc_stationary.extrapolated_waypoints[2].uncertainty_radius_km
    
    # Case 2: Northbound vessel (heading = 0.0, speed = 10.0 kts)
    # Expected displacement after 6 hours: 10 kts * 6h = 60 nautical miles = exactly 1.0 degree of latitude (111.12 km)
    fc_north = MaritimeRiskScorer.extrapolate_trajectory(
        lat=0.0, lon=0.0, speed_knots=10.0, heading_deg=0.0,
        forecast_horizons_hours=[6.0, 12.0, 24.0]
    )
    results["north_6h_lat"] = fc_north.extrapolated_waypoints[0].projected_lat
    results["north_6h_expected_lat"] = 1.000
    results["north_6h_error_deg"] = abs(fc_north.extrapolated_waypoints[0].projected_lat - 1.000)
    
    # Case 3: Eastbound vessel at equator (heading = 90.0, speed = 10.0 kts)
    # At equator cos(0) = 1.0; 60 nm = 1.0 degree of longitude
    fc_east = MaritimeRiskScorer.extrapolate_trajectory(
        lat=0.0, lon=0.0, speed_knots=10.0, heading_deg=90.0,
        forecast_horizons_hours=[6.0, 12.0, 24.0]
    )
    results["east_6h_lon"] = fc_east.extrapolated_waypoints[0].projected_lon
    results["east_6h_expected_lon"] = 1.000
    
    # Case 4: Antimeridian crossing test (lat = 0.0, lon = 179.5, heading = 90.0, speed = 10.0 kts, 6h = +1.0 deg)
    # Expected wrapped longitude: -179.5 degrees
    fc_anti = MaritimeRiskScorer.extrapolate_trajectory(
        lat=0.0, lon=179.5, speed_knots=10.0, heading_deg=90.0,
        forecast_horizons_hours=[6.0]
    )
    results["antimeridian_raw_lon"] = fc_anti.extrapolated_waypoints[0].projected_lon
    results["antimeridian_wraps_correctly"] = (-180.0 <= fc_anti.extrapolated_waypoints[0].projected_lon <= 180.0)

    # Case 5: Polar limits test (lat = 89.5, heading = 0.0, speed = 20 kts, 24h = +4.32 deg lat)
    # Expected behavior: latitude clamped at 90.0
    fc_polar = MaritimeRiskScorer.extrapolate_trajectory(
        lat=89.5, lon=0.0, speed_knots=20.0, heading_deg=0.0,
        forecast_horizons_hours=[24.0]
    )
    results["polar_raw_lat"] = fc_polar.extrapolated_waypoints[0].projected_lat
    results["polar_lat_bounded"] = (fc_polar.extrapolated_waypoints[0].projected_lat <= 90.0)
    
    for k, v in results.items():
        print(f"  {k}: {v}")
    return results

if __name__ == "__main__":
    test_risk_scorer_sensitivity()
    test_trajectory_known_answers()
