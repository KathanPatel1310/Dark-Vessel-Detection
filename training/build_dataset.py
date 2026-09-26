"""Maritime Intelligence Instruction-Tuning Dataset Generator (Pillar 3 Preparation).
Generates deterministic, mathematically grounded instruction datasets in standard
JSONL chat format for supervised fine-tuning (SFT) of Qwen 2.5 foundation models.

Scenarios Covered:
1. NORMAL_CORRELATED: Legitimate commercial vessels with valid transponders.
2. DELIBERATE_DARK_EVASION: Unmatched commercial hulls operating dark in deep waters.
3. SANCTIONED_VESSEL: Matched against official OFAC SDN / UN Consolidated watchlists.
4. AIS_GAP_SUSPICIOUS: Vessels with recent unexplained transponder outages near STS zones.
5. DEGRADED_EVIDENCE: Sensor loss, missing AIS telemetry, or offline registry feeds.
6. SMALL_CRAFT_EXEMPT: Dhows/artisanal fishing craft legally exempt under SOLAS V/19.
"""

import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Any

from src.schemas.sar import SARDetection
from src.schemas.ais import AISObservation, AISGap
from src.schemas.sanctions import SanctionMatch, SanctionsResult
from src.geospatial.eez_checker import RealEEZChecker
from src.features.pipeline import FeaturePipeline
from src.analytics.risk_scorer import MaritimeRiskScorer
from src.agents.tools import generate_structured_report

SYSTEM_PROMPT = (
    "You are an expert maritime intelligence analyst synthesizing radar telemetry, "
    "AIS tracking, geospatial sovereignty data, and sanctions screening into formal, "
    "legally grounded maritime surveillance bulletins. Ensure every conclusion is directly "
    "grounded in sensor evidence and applicable maritime statutes (UNCLOS Art. 73, SOLAS V/19, OFAC)."
)


def _generate_scenario(index: int, scenario_type: str, seed_offset: int = 0) -> Dict[str, Any]:
    """Generates a single deterministic training instance using project schemas and formulas."""
    now = datetime(2026, 9, 20, 12, 0, 0, tzinfo=timezone.utc)
    eez_checker = RealEEZChecker()

    if scenario_type == "NORMAL_CORRELATED":
        lat = 18.90 + (index * 0.05)
        lon = 72.70 + (index * 0.03)
        length = 120.0 + (index % 5) * 10
        mmsi = f"41900{1000 + index}"
        imo = f"912{1000 + index}"
        
        sar_det = SARDetection(
            detection_id=f"SAR-NORM-{index:03d}",
            scene_id="S1A_SCENE_NORM",
            timestamp=now,
            latitude=lat,
            longitude=lon,
            length_m=length,
            width_m=length / 5.5,
            aspect_ratio=5.5,
            heading_deg=180.0,
            confidence=0.96
        )
        ais_obs = AISObservation(
            mmsi=mmsi,
            imo=imo,
            vessel_name=f"MERCHANT-{index}",
            ship_type="Cargo",
            latitude=lat + 0.005,
            longitude=lon + 0.005,
            sog=12.5,
            cog=182.0,
            timestamp=now
        )
        geo_ctx = eez_checker.get_geo_context(lat, lon)
        features = FeaturePipeline.extract(sar_detection=sar_det, geo_context=geo_ctx, candidate_ais=ais_obs)
        sanctions_res = SanctionsResult(query_target=imo, is_sanctioned=False, overall_sanctions_risk="CLEAN", matches=[])
        degradations = []

    elif scenario_type == "DELIBERATE_DARK_EVASION":
        lat = 19.30 + (index * 0.04)
        lon = 62.10 + (index * 0.04) # Deep Arabian Sea
        length = 180.0 + (index % 6) * 15
        
        sar_det = SARDetection(
            detection_id=f"SAR-DARK-{index:03d}",
            scene_id="S1A_SCENE_DARK",
            timestamp=now,
            latitude=lat,
            longitude=lon,
            length_m=length,
            width_m=length / 5.8,
            aspect_ratio=5.8,
            heading_deg=240.0,
            confidence=0.92
        )
        ais_obs = None # Dark
        geo_ctx = eez_checker.get_geo_context(lat, lon)
        features = FeaturePipeline.extract(sar_detection=sar_det, geo_context=geo_ctx, candidate_ais=None)
        sanctions_res = SanctionsResult(query_target="UNKNOWN_DARK", is_sanctioned=False, overall_sanctions_risk="UNKNOWN", matches=[])
        degradations = ["AIS telemetry stream absent in spatio-temporal correlation window."]

    elif scenario_type == "SANCTIONED_VESSEL":
        lat = 24.10 + (index * 0.02)
        lon = 58.40 + (index * 0.03) # Gulf of Oman / STS zone
        length = 220.0 + (index % 4) * 20
        mmsi = f"67700{2000 + index}"
        imo = f"928472{index % 10}"
        
        sar_det = SARDetection(
            detection_id=f"SAR-SANC-{index:03d}",
            scene_id="S1A_SCENE_SANC",
            timestamp=now,
            latitude=lat,
            longitude=lon,
            length_m=length,
            width_m=length / 6.0,
            aspect_ratio=6.0,
            heading_deg=145.0,
            confidence=0.94
        )
        ais_obs = AISObservation(
            mmsi=mmsi,
            imo=imo,
            vessel_name=f"SHADOW TANKER {index}",
            ship_type="Tanker",
            latitude=lat + 0.01,
            longitude=lon + 0.01,
            sog=8.2,
            cog=140.0,
            timestamp=now
        )
        geo_ctx = eez_checker.get_geo_context(lat, lon)
        features = FeaturePipeline.extract(sar_detection=sar_det, geo_context=geo_ctx, candidate_ais=ais_obs, prior_sanctions=True)
        sanction_match = SanctionMatch(
            source_list="OFAC_SDN",
            entity_name=f"SHADOW TANKER {index}",
            entity_type="VESSEL",
            matched_imo=imo,
            sanction_programs=["IRAN-EO13846"],
            match_score=1.0,
            match_basis="EXACT_IMO_MATCH",
            remarks="Operated in support of sanctioned crude oil transport."
        )
        sanctions_res = SanctionsResult(
            query_target=imo,
            is_sanctioned=True,
            overall_sanctions_risk="CONFIRMED",
            matches=[sanction_match],
            screening_notes=f"Confirmed match on OFAC SDN registry under IRAN-EO13846."
        )
        degradations = []

    elif scenario_type == "AIS_GAP_SUSPICIOUS":
        lat = 20.10 + (index * 0.03)
        lon = 65.50 + (index * 0.04)
        length = 150.0 + (index % 5) * 12
        mmsi = f"35500{3000 + index}"
        
        sar_det = SARDetection(
            detection_id=f"SAR-GAP-{index:03d}",
            scene_id="S1A_SCENE_GAP",
            timestamp=now,
            latitude=lat,
            longitude=lon,
            length_m=length,
            width_m=length / 5.2,
            aspect_ratio=5.2,
            heading_deg=90.0,
            confidence=0.90
        )
        historical_gaps = [
            AISGap(
                mmsi=mmsi,
                gap_start=now,
                duration_hours=18.5 + (index % 10),
                start_lat=lat,
                start_lon=lon,
                is_suspicious=True
            )
        ]
        geo_ctx = eez_checker.get_geo_context(lat, lon)
        features = FeaturePipeline.extract(
            sar_detection=sar_det,
            geo_context=geo_ctx,
            candidate_ais=None,
            historical_gaps=historical_gaps
        )
        sanctions_res = SanctionsResult(query_target=mmsi, is_sanctioned=False, overall_sanctions_risk="CLEAN", matches=[])
        degradations = ["Active AIS gap ongoing for > 18 hours."]

    elif scenario_type == "SMALL_CRAFT_EXEMPT":
        lat = 21.05 + (index * 0.02)
        lon = 70.15 + (index * 0.02) # Close inshore off Gujarat coast (< 25km)
        length = 19.5 + (index % 5) # < 30m
        
        sar_det = SARDetection(
            detection_id=f"SAR-DHOW-{index:03d}",
            scene_id="S1A_SCENE_DHOW",
            timestamp=now,
            latitude=lat,
            longitude=lon,
            length_m=length,
            width_m=4.5,
            aspect_ratio=4.33,
            heading_deg=45.0,
            confidence=0.88
        )
        geo_ctx = eez_checker.get_geo_context(lat, lon)
        features = FeaturePipeline.extract(sar_detection=sar_det, geo_context=geo_ctx, candidate_ais=None)
        sanctions_res = SanctionsResult(query_target="COASTAL_CRAFT", is_sanctioned=False, overall_sanctions_risk="CLEAN", matches=[])
        degradations = []

    else: # DEGRADED_EVIDENCE
        lat = 17.50 + (index * 0.03)
        lon = 68.20 + (index * 0.03)
        length = 135.0
        sar_det = SARDetection(
            detection_id=f"SAR-DEGR-{index:03d}",
            scene_id="S1A_SCENE_DEGR",
            timestamp=now,
            latitude=lat,
            longitude=lon,
            length_m=length,
            width_m=22.0,
            aspect_ratio=6.1,
            heading_deg=310.0,
            confidence=0.82
        )
        geo_ctx = eez_checker.get_geo_context(lat, lon)
        features = FeaturePipeline.extract(sar_detection=sar_det, geo_context=geo_ctx, candidate_ais=None)
        sanctions_res = SanctionsResult(
            query_target="UNVERIFIED",
            is_sanctioned=False,
            overall_sanctions_risk="CLEAN",
            matches=[],
            screening_notes="DEGRADED_MODE: Registry lookup service unavailable. Baseline evaluation."
        )
        degradations = ["AIS feed offline", "Sanctions registry server unreachable"]

    # Compute risk and forecast
    risk_assessment = MaritimeRiskScorer.compute_risk_assessment(features, sanctions_res, geo_ctx)
    forecast = MaritimeRiskScorer.extrapolate_trajectory(
        lat=geo_ctx.latitude,
        lon=geo_ctx.longitude,
        speed_knots=10.0,
        heading_deg=sar_det.heading_deg or 180.0,
        start_time=now
    )

    report = generate_structured_report(
        mission_id=f"MSN-TRAIN-{index:03d}",
        target_detection_id=sar_det.detection_id,
        features=features,
        risk_assessment=risk_assessment,
        sanctions_result=sanctions_res,
        geo_context=geo_ctx,
        forecast=forecast,
        degradation_notes=degradations,
        human_in_the_loop=(risk_assessment.overall_anomaly_score >= 0.70 or sanctions_res.is_sanctioned),
        detection_confidence=sar_det.confidence
    )

    # Build the prompt input payload
    user_prompt = (
        f"ANALYZE MARITIME TARGET TELEMETRY:\n"
        f"- Target Detection ID: {sar_det.detection_id}\n"
        f"- Radar Coordinates: Lat {sar_det.latitude:.4f}, Lon {sar_det.longitude:.4f}\n"
        f"- SAR Dimensions: Length {sar_det.length_m:.1f}m, Beam {sar_det.width_m:.1f}m, Aspect Ratio {sar_det.aspect_ratio:.2f}\n"
        f"- Radar Confidence: {sar_det.confidence:.2f}\n"
        f"- AIS Broadcast Status: {'Active Match' if features.fusion.is_spatially_correlated else 'Unmatched / Dark'}\n"
        f"- Correlated MMSI: {features.mmsi_candidate or 'None'}\n"
        f"- Jurisdiction: {'INSIDE sovereign EEZ (' + str(geo_ctx.eez_country) + ')' if geo_ctx.inside_eez else 'International Waters'}\n"
        f"- Distance to Coast: {geo_ctx.distance_to_coast_km:.1f} km\n"
        f"- Sanctions Hit: {sanctions_res.is_sanctioned} ({sanctions_res.overall_sanctions_risk})\n"
        f"- Telemetry Degradation Notes: {degradations or 'None'}\n\n"
        f"Generate the validated, structured Intelligence Bulletin JSON."
    )

    # Build assistant target output (JSON format)
    assistant_output = report.model_dump_json(indent=2)

    return {
        "id": f"MAR-SFT-{index:04d}",
        "scenario_type": scenario_type,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": assistant_output}
        ],
        "ground_truth_metadata": {
            "target_detection_id": sar_det.detection_id,
            "threat_tier": report.threat_tier,
            "dark_vessel_classification": risk_assessment.dark_vessel_classification,
            "dark_vessel_probability": risk_assessment.dark_vessel_probability,
            "overall_anomaly_score": risk_assessment.overall_anomaly_score,
            "is_sanctioned": sanctions_res.is_sanctioned,
            "statutory_violations": report.statutory_violations,
            "inside_eez": geo_ctx.inside_eez
        }
    }


def build_instruction_dataset(
    output_dir: str = "training/data",
    train_count: int = 50,
    val_count: int = 15
):
    """
    Builds balanced, reproducible train and validation datasets across all 6 maritime scenarios.
    """
    os.makedirs(output_dir, exist_ok=True)
    scenarios = [
        "NORMAL_CORRELATED",
        "DELIBERATE_DARK_EVASION",
        "SANCTIONED_VESSEL",
        "AIS_GAP_SUSPICIOUS",
        "DEGRADED_EVIDENCE",
        "SMALL_CRAFT_EXEMPT"
    ]

    # Generate training examples
    train_file = os.path.join(output_dir, "maritime_train.jsonl")
    with open(train_file, "w", encoding="utf-8") as f:
        for i in range(train_count):
            scenario = scenarios[i % len(scenarios)]
            record = _generate_scenario(index=i + 1, scenario_type=scenario, seed_offset=0)
            f.write(json.dumps(record) + "\n")

    # Generate validation examples (held-out seeds)
    val_file = os.path.join(output_dir, "maritime_validation.jsonl")
    with open(val_file, "w", encoding="utf-8") as f:
        for i in range(val_count):
            scenario = scenarios[i % len(scenarios)]
            record = _generate_scenario(index=train_count + i + 1, scenario_type=scenario, seed_offset=1000)
            f.write(json.dumps(record) + "\n")

    print(f"Generated {train_count} training examples at: {train_file}")
    print(f"Generated {val_count} validation examples at: {val_file}")


if __name__ == "__main__":
    build_instruction_dataset()
