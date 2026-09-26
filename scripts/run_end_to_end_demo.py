"""Offline End-to-End Vertical Slice Demonstration.
Executes the unified maritime intelligence pipeline:
1. Ingests offline deterministic fixtures (SAR, AIS, Sanctions).
2. Extracts mathematical features across all 5 domains (Pillar 1).
3. Executes the LangGraph multi-agent decision state graph (Pillar 2).
4. Prints the complete agent execution trace.
5. Prints the engineered feature vector.
6. Prints the multi-factor risk assessment and sanctions findings.
7. Prints the structured legal intelligence bulletin (Pillar 3 target schema).
8. Clearly identifies operational disposition: NORMAL, DEGRADED, or AWAITING_HUMAN_REVIEW.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Dict, Any

from src.schemas.mission import Mission, BoundingBox
from src.schemas.sar import SARDetection
from src.schemas.ais import AISObservation, AISGap
from src.schemas.state import MaritimeAgentState
from src.agents.graph import build_maritime_intelligence_graph
from src.geospatial.eez_checker import RealEEZChecker


def run_demo(
    sar_fixture_path: str = "data/fixtures/synthetic_sar_detections.json",
    ais_fixture_path: str = "data/fixtures/synthetic_ais_tracks.json",
    target_detection_id: str = "SAR-DET-2026-001",
    simulate_sanctions_offline: bool = False
):
    print("=" * 80)
    print(" DARK VESSEL DETECTION & MARITIME INTELLIGENCE SYSTEM")
    print(" OFFLINE END-TO-END VERTICAL SLICE DEMONSTRATION")
    print("=" * 80)

    # 1. Load Fixtures
    print(f"\n[1] Loading SAR Detection Fixture from: {sar_fixture_path}")
    if not os.path.exists(sar_fixture_path):
        raise FileNotFoundError(f"Fixture not found: {sar_fixture_path}")

    with open(sar_fixture_path, "r", encoding="utf-8") as f:
        sar_data = json.load(f)

    target_sar_dict = None
    for d in sar_data["detections"]:
        if d["detection_id"] == target_detection_id:
            target_sar_dict = d
            break
    if not target_sar_dict:
        target_sar_dict = sar_data["detections"][0]

    sar_detection = SARDetection(**target_sar_dict)
    print(f"  Loaded SAR Target: {sar_detection.detection_id}")
    print(f"    - Coordinates : ({sar_detection.latitude:.4f}, {sar_detection.longitude:.4f})")
    print(f"    - Hull Length : {sar_detection.length_m:.1f} m, Beam: {sar_detection.width_m:.1f} m, Aspect Ratio: {sar_detection.aspect_ratio:.2f}")
    print(f"    - Timestamp   : {sar_detection.timestamp}")

    print(f"\n[2] Loading AIS Tracking Fixture from: {ais_fixture_path}")
    matched_ais = None
    historical_gaps = []
    if os.path.exists(ais_fixture_path):
        with open(ais_fixture_path, "r", encoding="utf-8") as f:
            ais_data = json.load(f)
        broadcasts = [AISObservation(**b) for b in ais_data.get("active_broadcasts", [])]
        historical_gaps = [AISGap(**g) for g in ais_data.get("historical_gaps", [])]

        # Check if any active broadcast correlates with this target
        for b in broadcasts:
            from src.geospatial.eez_checker import haversine_km
            dist = haversine_km(sar_detection.latitude, sar_detection.longitude, b.latitude, b.longitude)
            if dist <= 15.0:
                matched_ais = b
                break

    if matched_ais:
        print(f"  Correlated AIS Broadcast Found: MMSI {matched_ais.mmsi} ({matched_ais.vessel_name})")
    else:
        print("  No Correlated AIS Broadcast Found -> Evaluating in Dark Vessel Investigation Mode.")

    # 2. Initialize LangGraph Workflow
    print("\n[3] Initializing LangGraph Multi-Agent Workflow State...")
    mission = Mission(
        mission_id="MSN-DEMO-2026-01",
        name="Arabian Sea Maritime Security Patrol",
        time_window_start=sar_detection.timestamp,
        time_window_end=sar_detection.timestamp,
        bbox=BoundingBox(min_lat=12.0, max_lat=24.0, min_lon=58.0, max_lon=74.0)
    )

    degradations = []
    if simulate_sanctions_offline:
        degradations.append("sanctions_offline_simulated")

    initial_state = MaritimeAgentState(
        mission=mission,
        active_detection=sar_detection,
        matched_ais_observation=matched_ais,
        historical_gaps=historical_gaps,
        degradation_notes=degradations
    )

    print("\n[4] Executing Compiled StateGraph (6 Typed Agent Nodes + HITL Gate)...")
    graph = build_maritime_intelligence_graph()
    final_state = graph.invoke(initial_state)

    # 3. Print Agent Execution Trace
    print("\n" + "-" * 80)
    print("MULTI-AGENT EXECUTION TRACE")
    print("-" * 80)
    trace_entries = final_state.get("execution_trace", [])
    for t in trace_entries:
        status_tag = f"[{t.status}]"
        print(f"  Step {t.step_number:02d} | {t.agent_name:<22} | {status_tag:<10} | {t.action_taken}")
        if t.notes:
            print(f"          Notes: {t.notes}")

    # 4. Print Engineered Feature Summary
    features = final_state.get("engineered_features")
    print("\n" + "-" * 80)
    print("PILLAR 1: ENGINEERED MATHEMATICAL FEATURES")
    print("-" * 80)
    if features:
        print(f"  [SAR Morphology & Radiometry]")
        print(f"    - Target-to-Clutter Ratio : {features.sar.target_to_clutter_ratio_db or 0.0:.2f} dB")
        print(f"    - Aspect Ratio (L/B)      : {features.sar.aspect_ratio:.2f}")
        print(f"    - Radar Target Area       : {features.sar.detection_area_m2:.1f} m^2")
        print(f"    - Compactness & Eccentricity: {features.sar.compactness or 0.0:.3f}, {features.sar.eccentricity or 0.0:.3f}")
        print(f"  [AIS Kinematics & Forensics]")
        if features.ais:
            print(f"    - Mean SOG & Variance     : {features.ais.mean_speed_knots:.1f} kts (var: {features.ais.speed_variance:.2f})")
            print(f"    - Current Outage Duration : {features.ais.current_gap_duration_hours:.1f} hrs")
            print(f"    - Historical Gaps (30d)   : {features.ais.ais_gap_count_30d}")
        print(f"  [Geospatial Sovereignty]")
        print(f"    - Inside Sovereign EEZ    : {features.geospatial.is_inside_eez}")
        print(f"    - Distance to Coastline   : {features.geospatial.distance_to_shore_km:.1f} km")
        print(f"    - Nearest Port Distance   : {features.geospatial.distance_to_nearest_port_km or 0.0:.1f} km")
        print(f"    - STS Corridor Proximity  : {features.geospatial.proximity_to_sts_corridor_km or 0.0:.1f} km")
        print(f"  [SAR-AIS Fusion Deltas]")
        print(f"    - Spatial Discrepancy     : {features.fusion.spatial_discrepancy_km:.1f} km")
        print(f"    - Spatially Correlated    : {features.fusion.is_spatially_correlated}")

    # 5. Print Risk & Sanctions Findings
    risk = final_state.get("risk_assessment")
    sanctions = final_state.get("sanctions_result")
    print("\n" + "-" * 80)
    print("ANALYTICAL RISK SCORING & SANCTIONS FINDINGS")
    print("-" * 80)
    if risk:
        print(f"  - Dark Vessel Classification : {risk.dark_vessel_classification}")
        print(f"  - Dark Vessel Probability    : {risk.dark_vessel_probability * 100:.1f}%")
        print(f"  - Overall Anomaly Score      : {risk.overall_anomaly_score:.2f} / 1.00")
        print(f"  - Sanctions Risk Level       : {risk.sanctions_risk_level}")
        print(f"  - EEZ Threat Level           : {risk.eez_threat_level}")
        print(f"  - Evidential Risk Triggers   : {risk.risk_factors}")
    if sanctions:
        print(f"  - Sanctions Match Confirmed  : {sanctions.is_sanctioned} ({sanctions.overall_sanctions_risk})")
        print(f"  - Screening Authority Notes  : {sanctions.screening_notes}")

    # 6. Print Structured Report
    report = final_state.get("final_report")
    print("\n" + "-" * 80)
    print("PILLAR 3: STRUCTURED INTELLIGENCE BULLETIN (TARGET FORMAT)")
    print("-" * 80)
    if report:
        print(f"  Report ID        : {report.report_id}")
        print(f"  Threat Tier      : {report.threat_tier}")
        print(f"  Executive Summary: {report.executive_summary}\n")
        print(f"  Characteristics  : {report.vessel_characteristics_summary}")
        print(f"  AIS Telemetry    : {report.ais_status_summary}")
        print(f"  Sanctions Status : {report.sanctions_findings}")
        print(f"  Geospatial Scope : {report.geospatial_eez_analysis}\n")
        print(f"  Statutory Violations Cited:")
        for s in report.statutory_violations:
            print(f"    * {s}")
        print(f"\n  Actionable Recommendations:")
        for r in report.actionable_recommendations:
            print(f"    -> {r}")
        print(f"\n  Predictive Dead-Reckoning Forecast (+6h, +12h, +24h):")
        for wp in report.predictive_forecast.extrapolated_waypoints:
            print(f"    Waypoint +{wp.projection_hours:02.0f}h: ({wp.projected_lat:.4f}, {wp.projected_lon:.4f}) [Error Cone: {wp.uncertainty_radius_km:.1f} km]")

    # 7. Identify Operational State
    hitl_flag = final_state.get("human_in_the_loop_flag", False)
    degradations = final_state.get("degradation_notes", [])
    
    print("\n" + "=" * 80)
    print("OPERATIONAL DISPOSITION SUMMARY")
    print("=" * 80)
    if hitl_flag:
        print("  STATUS: [AWAITING HUMAN REVIEW / HIGH-RISK ESCALATION]")
        print("  REASON: Target exceeds risk threshold (Anomaly Score >= 0.70 or Deliberate Dark Evasion).")
        print(f"  FEEDBACK: {final_state.get('human_feedback')}")
    elif degradations:
        print("  STATUS: [DEGRADED OPERATION]")
        print(f"  REASON: Executed successfully with {len(degradations)} telemetry degradation condition(s).")
    else:
        print("  STATUS: [NORMAL]")
        print("  REASON: All sensor feeds correlated, verified benign commercial traffic.")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Offline End-to-End Maritime Intelligence Demo")
    parser.add_argument("--sar_fixture", type=str, default="data/fixtures/synthetic_sar_detections.json")
    parser.add_argument("--ais_fixture", type=str, default="data/fixtures/synthetic_ais_tracks.json")
    parser.add_argument("--target_id", type=str, default="SAR-DET-2026-001", help="Detection ID to evaluate (e.g. SAR-DET-2026-001 for dark vessel, SAR-DET-2026-002 for benign vessel)")
    parser.add_argument("--simulate_sanctions_offline", action="store_true", help="Simulate unavailable sanctions database")
    args = parser.parse_args()

    run_demo(
        sar_fixture_path=args.sar_fixture,
        ais_fixture_path=args.ais_fixture,
        target_detection_id=args.target_id,
        simulate_sanctions_offline=args.simulate_sanctions_offline
    )
