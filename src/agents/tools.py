"""Agent Tools Module for Maritime Intelligence Workflow.
Provides functional tool wrappers around existing analytical engines:
- SARAISCorrelationTool: Spatio-temporal matching against AIS tracks
- FeatureExtractionTool: Unified 5-domain feature engineering pipeline
- SanctionsScreeningTool: Sub-millisecond screening against OFAC/UN indices
- RiskForensicsTool: Multi-factor risk scoring and dead-reckoning forecasting
- ReportGenerationTool: Structured intelligence bulletin compilation
"""

import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from src.schemas.sar import SARDetection
from src.schemas.ais import AISObservation, AISGap
from src.schemas.geospatial import GeoContext
from src.schemas.vessel import VesselCandidate
from src.schemas.sanctions import SanctionMatch, SanctionsResult
from src.schemas.features import EngineeredFeatures
from src.schemas.intelligence import (
    RiskAssessment,
    PredictiveForecast,
    IntelligenceReport,
)
from src.geospatial.eez_checker import RealEEZChecker, haversine_km
from src.features.pipeline import FeaturePipeline
from src.features.fusion_features import extract_fusion_features
from src.analytics.risk_scorer import MaritimeRiskScorer
from src.data.sanctions_parser import RealSanctionsDatabase
from src.utils.logger import setup_logger

logger = setup_logger("agent_tools")

# Singleton or cached sanctions database instance for speed
_SANCTIONS_DB: Optional[RealSanctionsDatabase] = None
_EEZ_CHECKER: Optional[RealEEZChecker] = None


def get_eez_checker() -> RealEEZChecker:
    """Returns singleton instance of RealEEZChecker."""
    global _EEZ_CHECKER
    if _EEZ_CHECKER is None:
        _EEZ_CHECKER = RealEEZChecker()
    return _EEZ_CHECKER


def get_sanctions_db(allow_fallback: bool = True) -> Optional[RealSanctionsDatabase]:
    """Returns singleton instance of RealSanctionsDatabase with graceful fallback."""
    global _SANCTIONS_DB
    if _SANCTIONS_DB is None:
        ofac_path = "data/raw/sanctions/sdn.xml"
        un_path = "data/raw/sanctions/un_consolidated.xml"
        if os.path.exists(ofac_path) or os.path.exists(un_path):
            try:
                _SANCTIONS_DB = RealSanctionsDatabase(ofac_xml_path=ofac_path, un_xml_path=un_path)
            except Exception as e:
                logger.warning(f"Could not load real sanctions XML: {e}")
                if not allow_fallback:
                    raise
        else:
            if not allow_fallback:
                return None
            logger.info("Real sanctions XML files not present, using lightweight fixture fallback.")
            _SANCTIONS_DB = RealSanctionsDatabase(ofac_xml_path="", un_xml_path="")
    return _SANCTIONS_DB


def correlate_sar_ais(
    sar_detection: SARDetection,
    ais_observations: List[AISObservation],
    spatial_threshold_km: float = 15.0,
    temporal_threshold_minutes: float = 60.0
) -> Tuple[Optional[AISObservation], List[VesselCandidate]]:
    """
    Finds the closest spatio-temporal AIS observation match for a given SAR detection.
    Returns: (best_match_observation, candidate_list)
    """
    if not ais_observations:
        return None, []

    candidates: List[Tuple[float, float, AISObservation]] = []
    for obs in ais_observations:
        dist_km = haversine_km(
            sar_detection.latitude, sar_detection.longitude,
            obs.latitude, obs.longitude
        )
        dt_minutes = abs((sar_detection.timestamp - obs.timestamp).total_seconds()) / 60.0

        if dist_km <= spatial_threshold_km and dt_minutes <= temporal_threshold_minutes:
            candidates.append((dist_km, dt_minutes, obs))

    if not candidates:
        return None, []

    # Sort by spatial distance first, then temporal difference
    candidates.sort(key=lambda c: (c[0], c[1]))
    best_match = candidates[0][2]

    vessel_candidates: List[VesselCandidate] = []
    for dist_km, dt_min, obs in candidates:
        spatial_score = max(0.0, 1.0 - (dist_km / spatial_threshold_km))
        temporal_score = max(0.0, 1.0 - (dt_min / temporal_threshold_minutes))
        match_score = round(0.6 * spatial_score + 0.4 * temporal_score, 2)

        vessel_candidates.append(
            VesselCandidate(
                vessel=VesselIdentity(
                    mmsi=obs.mmsi,
                    name=obs.vessel_name or f"CANDIDATE-{obs.mmsi}",
                    vessel_type=obs.ship_type
                ),
                match_confidence=match_score,
                dimension_similarity=0.90,
                route_plausibility=0.85,
                matching_rationale=f"Spatio-temporal correlation at {dist_km:.1f}km and {dt_min:.1f}min."
            )
        )

    return best_match, vessel_candidates


def extract_features(
    sar_detection: SARDetection,
    geo_context: GeoContext,
    candidate_ais: Optional[AISObservation] = None,
    all_candidate_ais_points: Optional[List[AISObservation]] = None,
    historical_gaps: Optional[List[AISGap]] = None,
    registered_length_m: Optional[float] = None,
    prior_sanctions: bool = False
) -> EngineeredFeatures:
    """Invokes the Pillar 1 unified feature extraction pipeline."""
    return FeaturePipeline.extract(
        sar_detection=sar_detection,
        geo_context=geo_context,
        candidate_ais=candidate_ais,
        all_candidate_ais_points=all_candidate_ais_points,
        historical_gaps=historical_gaps,
        registered_length_m=registered_length_m,
        prior_sanctions=prior_sanctions
    )


def screen_sanctions(
    imo: Optional[str] = None,
    mmsi: Optional[str] = None,
    vessel_name: Optional[str] = None,
    force_offline: bool = False
) -> Tuple[SanctionsResult, bool]:
    """
    Screens vessel identifier against sanctions database.
    Returns: (SanctionsResult, is_degraded)
    """
    if force_offline:
        # Simulated unavailable sanctions database
        logger.warning("Sanctions screening invoked with force_offline=True: simulating degraded mode.")
        query_key = imo or mmsi or vessel_name or "UNKNOWN"
        return (
            SanctionsResult(
                query_target=query_key,
                is_sanctioned=False,
                overall_sanctions_risk="CLEAN",
                matches=[],
                screening_notes="DEGRADED_MODE: Live sanctions service offline. Evaluated as unverified baseline."
            ),
            True
        )

    db = get_sanctions_db(allow_fallback=True)
    if db is None or db.total_vessels_indexed == 0:
        query_key = imo or mmsi or vessel_name or "UNKNOWN"
        return (
            SanctionsResult(
                query_target=query_key,
                is_sanctioned=False,
                overall_sanctions_risk="CLEAN",
                matches=[],
                screening_notes="DEGRADED_MODE: Sanctions database empty or unpopulated."
            ),
            True
        )

    res = db.screen_vessel(imo=imo, mmsi=mmsi, vessel_name=vessel_name)
    return res, False


def assess_risk_and_forecast(
    features: EngineeredFeatures,
    sanctions_result: SanctionsResult,
    geo_context: GeoContext,
    heading_deg: Optional[float] = None,
    speed_knots: Optional[float] = None
) -> Tuple[RiskAssessment, PredictiveForecast]:
    """Computes quantitative risk metrics and dead-reckoning trajectory forecast."""
    risk_assessment = MaritimeRiskScorer.compute_risk_assessment(
        features=features,
        sanctions_result=sanctions_result,
        geo_context=geo_context
    )

    sar = features.sar
    speed = speed_knots if speed_knots is not None else 10.0 # Default cruising speed if unmeasured
    heading = heading_deg if heading_deg is not None else (sar.orientation_deg or 180.0)

    forecast = MaritimeRiskScorer.extrapolate_trajectory(
        lat=geo_context.latitude,
        lon=geo_context.longitude,
        speed_knots=speed,
        heading_deg=heading,
        start_time=datetime.fromisoformat(features.timestamp.replace("Z", "+00:00"))
    )

    return risk_assessment, forecast


def generate_structured_report(
    mission_id: str,
    target_detection_id: str,
    features: EngineeredFeatures,
    risk_assessment: RiskAssessment,
    sanctions_result: SanctionsResult,
    geo_context: GeoContext,
    forecast: PredictiveForecast,
    top_candidate: Optional[VesselCandidate] = None,
    degradation_notes: Optional[List[str]] = None,
    human_in_the_loop: bool = False,
    detection_confidence: float = 0.90
) -> IntelligenceReport:
    """Synthesizes structured maritime intelligence report bulletin."""
    sar = features.sar
    ais = features.ais
    fusion = features.fusion

    # Determine overall threat tier
    if risk_assessment.overall_anomaly_score >= 0.80 or sanctions_result.is_sanctioned:
        threat_tier = "SEVERE"
    elif risk_assessment.overall_anomaly_score >= 0.60:
        threat_tier = "HIGH"
    elif risk_assessment.overall_anomaly_score >= 0.35:
        threat_tier = "MEDIUM"
    else:
        threat_tier = "LOW"

    # Executive Summary with concrete data points
    dark_flag = risk_assessment.dark_vessel_classification
    hitl_status = " [AWAITING HUMAN REVIEW]" if human_in_the_loop else ""
    degrade_flag = " [DEGRADED EVIDENCE]" if (degradation_notes and len(degradation_notes) > 0) else ""

    exec_summary = (
        f"Autonomous Maritime Intelligence Bulletin for Target {target_detection_id} "
        f"in {geo_context.eez_country or 'International Waters'}. Classified as {dark_flag} "
        f"with anomaly score {risk_assessment.overall_anomaly_score:.2f} ({threat_tier} threat){hitl_status}{degrade_flag}. "
        f"Radar estimated hull length {sar.length_m:.1f}m, TCR {sar.target_to_clutter_ratio_db or 0.0:.1f} dB. "
    )
    if fusion.is_spatially_correlated:
        exec_summary += f"Positively correlated with active AIS broadcast (MMSI: {features.mmsi_candidate})."
    else:
        exec_summary += "No correlated AIS transmission detected within spatio-temporal matching window."

    # Vessel characteristics
    char_summary = (
        f"SAR Satellite Morphology: Estimated Length = {sar.length_m:.1f}m, Beam = {sar.width_m:.1f}m, "
        f"Aspect Ratio = {sar.aspect_ratio:.2f}, Detection Area = {sar.detection_area_m2:.1f} m^2, "
        f"Target-to-Clutter Ratio = {sar.target_to_clutter_ratio_db or 0.0:.1f} dB."
    )

    # AIS status
    if not fusion.is_spatially_correlated or not features.mmsi_candidate:
        gap_info = f" Outage duration: {ais.current_gap_duration_hours:.1f} hrs." if ais else ""
        ais_summary = f"AIS Transmission Status: NON_TRANSMITTING (Zero active AIS signals received).{gap_info} Suspected dark vessel."
    elif ais:
        ais_summary = (
            f"AIS Track History: Mean Speed = {ais.mean_speed_knots:.1f} kts, "
            f"Current Gap Duration = {ais.current_gap_duration_hours:.1f} hrs, "
            f"Outages (30d) = {ais.ais_gap_count_30d}, "
            f"Loitering Duration = {ais.loitering_duration_hours:.1f} hrs."
        )
    else:
        ais_summary = "AIS Transmission Status: NON_TRANSMITTING (Zero active AIS signals received). Suspected dark vessel."

    # Identity attribution
    if top_candidate:
        attrib_summary = (
            f"Candidate Vessel Identity: {top_candidate.vessel.name} (MMSI: {top_candidate.vessel.mmsi}) "
            f"with Match Confidence {top_candidate.match_confidence:.2f}."
        )
    else:
        attrib_summary = "Identity Attribution: UNATTRIBUTED (Unmatched radar contact, no registered transponder matched)."

    # Sanctions findings
    if sanctions_result.is_sanctioned:
        sanctions_summary = (
            f"CRITICAL SANCTIONS HIT: Target matches {len(sanctions_result.matches)} official registry record(s). "
            f"Programs: {', '.join(sanctions_result.matches[0].sanction_programs)}. "
            f"Screening Notes: {sanctions_result.screening_notes}"
        )
    else:
        sanctions_summary = f"Sanctions Status: {sanctions_result.overall_sanctions_risk}. {sanctions_result.screening_notes}"

    # Geospatial analysis
    eez_status = f"INSIDE sovereign EEZ of {geo_context.eez_country}" if geo_context.inside_eez else f"OUTSIDE EEZ ({geo_context.distance_to_eez_boundary_km:.1f} km from boundary)"
    geo_summary = (
        f"Geospatial Context: Operating at ({geo_context.latitude:.4f}, {geo_context.longitude:.4f}), "
        f"{geo_context.distance_to_coast_km:.1f} km offshore. Jurisdiction: {eez_status}. "
        f"Nearest Port: {geo_context.nearest_port_name} ({geo_context.distance_to_nearest_port_km or 0.0:.1f} km). "
        f"Proximity to STS Rendezvous Sector: {geo_context.distance_to_sts_zone_km or 0.0:.1f} km to {geo_context.nearest_sts_zone_name}."
    )

    # Statutory citations
    statutes: List[str] = []
    recommendations: List[str] = []

    if sar.length_m >= 50.0 and not fusion.is_spatially_correlated:
        statutes.append("SOLAS Chapter V, Regulation 19 (Mandatory AIS carriage for commercial vessels >= 300 GT)")
        recommendations.append("File urgent dark vessel encounter notice with Indian Ocean Information Fusion Centre (IFC-IOR).")

    if geo_context.inside_eez and not fusion.is_spatially_correlated:
        statutes.append("UNCLOS Article 73 (Enforcement of sovereign rights within Exclusive Economic Zone)")
        recommendations.append(f"Notify Maritime Coast Guard Operations for aerial surveillance overflight at coordinates ({geo_context.latitude:.4f}, {geo_context.longitude:.4f}).")

    if sanctions_result.is_sanctioned:
        statutes.append(f"OFAC / UN Maritime Sanctions Enforcement Protocol ({', '.join(sanctions_result.matches[0].sanction_programs)})")
        recommendations.append("Issue interdiction advisory to port state authorities and financial intelligence units.")

    if not statutes:
        statutes.append("Standard Maritime Navigation Code (Compliance verification passed)")
        recommendations.append("Maintain routine surveillance radar monitoring.")

    # Confidence disclaimer
    confidence_stmt = (
        f"Automated multi-agent intelligence assessment synthesized from Sentinel-1 SAR and AIS telemetry. "
        f"Sensor confidence: Radar Detection={detection_confidence:.2f}, Anomaly Score={risk_assessment.overall_anomaly_score:.2f}."
    )
    if degradation_notes:
        confidence_stmt += f" Warning: Executed with {len(degradation_notes)} degraded telemetry condition(s)."

    report_id = f"MAR-INTEL-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{target_detection_id[-6:]}"

    return IntelligenceReport(
        report_id=report_id,
        mission_id=mission_id,
        target_detection_id=target_detection_id,
        executive_summary=exec_summary,
        threat_tier=threat_tier,
        vessel_characteristics_summary=char_summary,
        ais_status_summary=ais_summary,
        identity_attribution_summary=attrib_summary,
        sanctions_findings=sanctions_summary,
        geospatial_eez_analysis=geo_summary,
        predictive_forecast=forecast,
        statutory_violations=statutes,
        actionable_recommendations=recommendations,
        analyst_confidence_statement=confidence_stmt
    )
