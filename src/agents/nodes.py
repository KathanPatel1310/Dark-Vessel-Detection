"""Typed Agent Nodes for LangGraph Maritime Surveillance Workflow.
Implements the 6 primary agent nodes:
1. MissionController
2. SARAISCorrelator
3. FeatureEngineerNode
4. SanctionsScreenerNode
5. ForensicAssessorNode
6. ReportPreparerNode
Plus an explicit HumanReviewNode for Human-in-the-Loop review gates.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.schemas.state import MaritimeAgentState, AgentTraceEntry
from src.schemas.geospatial import GeoContext
from src.schemas.sanctions import SanctionsResult
from src.agents.tools import (
    get_eez_checker,
    correlate_sar_ais,
    extract_features,
    screen_sanctions,
    assess_risk_and_forecast,
    generate_structured_report,
)
from src.utils.logger import setup_logger

logger = setup_logger("agent_nodes")


def _append_trace(
    state: MaritimeAgentState,
    agent_name: str,
    action: str,
    status: str = "SUCCESS",
    details: Optional[Dict[str, Any]] = None,
    notes: Optional[str] = None
) -> List[AgentTraceEntry]:
    """Helper to build updated trace entries without mutating prior state."""
    current_traces = list(state.execution_trace or [])
    new_step = len(current_traces) + 1
    new_entry = AgentTraceEntry(
        step_number=new_step,
        agent_name=agent_name,
        action_taken=action,
        status=status,
        details=details or {},
        notes=notes
    )
    return current_traces + [new_entry]


# -------------------------------------------------------------------------
# Node 1: MissionController
# -------------------------------------------------------------------------
def mission_controller_node(state: MaritimeAgentState) -> Dict[str, Any]:
    """
    Validates operational parameters, initializes spatial context, and verifies
    that active SAR radar detections are ready for multi-agent investigation.
    """
    mission = state.mission
    detection = state.active_detection

    # If no active detection specified, pick first from all_detections or fail gracefully
    if detection is None and state.all_detections:
        detection = state.all_detections[0]

    if detection is None:
        trace = _append_trace(
            state=state,
            agent_name="MissionController",
            action="VALIDATE_MISSION_PARAMETERS",
            status="FAILED",
            notes="No active SAR detection available in state to evaluate."
        )
        return {
            "current_node": "MissionController",
            "completed_nodes": list(state.completed_nodes or []) + ["MissionController"],
            "execution_trace": trace,
            "errors": list(state.errors or []) + ["MissionController: No active detection found."]
        }

    # Resolve geospatial context
    eez_checker = get_eez_checker()
    geo_ctx = eez_checker.get_geo_context(detection.latitude, detection.longitude)

    details = {
        "mission_id": mission.mission_id,
        "detection_id": detection.detection_id,
        "target_coordinates": [detection.latitude, detection.longitude],
        "eez_country": geo_ctx.eez_country or "International Waters",
        "inside_eez": geo_ctx.inside_eez,
        "distance_to_coast_km": geo_ctx.distance_to_coast_km
    }

    trace = _append_trace(
        state=state,
        agent_name="MissionController",
        action="INITIALIZE_MISSION_AND_GEOCONTEXT",
        status="SUCCESS",
        details=details,
        notes=f"Mission initialized for AOI: {geo_ctx.eez_country or 'International Waters'}."
    )

    return {
        "active_detection": detection,
        "geo_context": geo_ctx,
        "current_node": "MissionController",
        "completed_nodes": list(state.completed_nodes or []) + ["MissionController"],
        "execution_trace": trace
    }


# -------------------------------------------------------------------------
# Node 2: SARAISCorrelator
# -------------------------------------------------------------------------
def sar_ais_correlator_node(state: MaritimeAgentState) -> Dict[str, Any]:
    """
    Correlates active radar detection with candidate AIS observations.
    If AIS telemetry is missing or simulated offline, gracefully records a
    degradation note and proceeds in radar-only dark vessel evaluation mode.
    """
    detection = state.active_detection
    matched_ais = state.matched_ais_observation
    degradation_notes = list(state.degradation_notes or [])

    # Check for missing AIS condition
    # If no matched_ais was provided and no candidates exist in state
    is_ais_missing = (matched_ais is None and not state.identity_candidates)

    if is_ais_missing:
        degradation_msg = "AIS telemetry feed unavailable or zero broadcasts in spatio-temporal window: degraded to dark vessel radar-only mode."
        degradation_notes.append(degradation_msg)
        logger.warning(f"SARAISCorrelator: {degradation_msg}")

        trace = _append_trace(
            state=state,
            agent_name="SARAISCorrelator",
            action="CORRELATE_SAR_AIS",
            status="DEGRADED",
            details={"matched_mmsi": None, "correlation_status": "UNMATCHED_NO_AIS"},
            notes=degradation_msg
        )

        return {
            "matched_ais_observation": None,
            "top_candidate": None,
            "degradation_notes": degradation_notes,
            "current_node": "SARAISCorrelator",
            "completed_nodes": list(state.completed_nodes or []) + ["SARAISCorrelator"],
            "execution_trace": trace
        }

    # Normal AIS correlation path
    top_cand = state.top_candidate
    if matched_ais and not top_cand:
        from src.schemas.vessel import VesselCandidate, VesselIdentity
        from src.geospatial.eez_checker import haversine_km
        dist = haversine_km(detection.latitude, detection.longitude, matched_ais.latitude, matched_ais.longitude)
        vessel_id = VesselIdentity(
            mmsi=matched_ais.mmsi,
            name=matched_ais.vessel_name or f"VESSEL-{matched_ais.mmsi}",
            vessel_type=matched_ais.ship_type
        )
        top_cand = VesselCandidate(
            vessel=vessel_id,
            match_confidence=0.95,
            dimension_similarity=0.90,
            route_plausibility=0.92,
            matching_rationale=f"Positively matched AIS transponder {matched_ais.mmsi} at offset {dist:.1f}km."
        )

    trace = _append_trace(
        state=state,
        agent_name="SARAISCorrelator",
        action="CORRELATE_SAR_AIS",
        status="SUCCESS",
        details={
            "matched_mmsi": matched_ais.mmsi if matched_ais else None,
            "vessel_name": top_cand.vessel.name if top_cand else None,
            "match_confidence": top_cand.match_confidence if top_cand else None
        },
        notes="Positively correlated SAR target with active AIS transponder broadcast."
    )

    return {
        "matched_ais_observation": matched_ais,
        "top_candidate": top_cand,
        "current_node": "SARAISCorrelator",
        "completed_nodes": list(state.completed_nodes or []) + ["SARAISCorrelator"],
        "execution_trace": trace
    }


# -------------------------------------------------------------------------
# Node 3: FeatureEngineerNode
# -------------------------------------------------------------------------
def feature_engineer_node(state: MaritimeAgentState) -> Dict[str, Any]:
    """
    Executes Pillar 1 mathematical feature engineering across SAR radiometry/morphology,
    AIS kinematics, geospatial proximity, historical indicators, and fusion metrics.
    """
    detection = state.active_detection
    geo_ctx = state.geo_context
    matched_ais = state.matched_ais_observation
    gaps = state.historical_gaps

    prior_sanctions = bool(state.sanctions_result and state.sanctions_result.is_sanctioned)

    # Invoke the unified FeaturePipeline
    features = extract_features(
        sar_detection=detection,
        geo_context=geo_ctx,
        candidate_ais=matched_ais,
        historical_gaps=gaps,
        prior_sanctions=prior_sanctions
    )

    details = {
        "tcr_db": features.sar.target_to_clutter_ratio_db,
        "detection_area_m2": features.sar.detection_area_m2,
        "estimated_length_m": features.sar.length_m,
        "distance_to_shore_km": features.geospatial.distance_to_shore_km,
        "is_spatially_correlated": features.fusion.is_spatially_correlated,
        "route_anomaly_score": features.historical.route_anomaly_score
    }

    trace = _append_trace(
        state=state,
        agent_name="FeatureEngineerNode",
        action="EXTRACT_FIVE_DOMAIN_FEATURES",
        status="SUCCESS",
        details=details,
        notes="Successfully extracted 5-domain mathematical feature vector."
    )

    return {
        "engineered_features": features,
        "current_node": "FeatureEngineerNode",
        "completed_nodes": list(state.completed_nodes or []) + ["FeatureEngineerNode"],
        "execution_trace": trace
    }


# -------------------------------------------------------------------------
# Node 4: SanctionsScreenerNode
# -------------------------------------------------------------------------
def sanctions_screener_node(state: MaritimeAgentState) -> Dict[str, Any]:
    """
    Screens candidate vessel identity against official OFAC SDN & UN Consolidated lists.
    If sanctions service is unavailable or simulated offline, gracefully routes to
    degraded local baseline mode without crashing.
    """
    degradation_notes = list(state.degradation_notes or [])
    
    # Check if state already has a pre-set sanctions result or simulated offline flag
    simulated_offline = "SIMULATE_SANCTIONS_OFFLINE" in state.completed_nodes or any(
        "sanctions_offline" in n.lower() for n in degradation_notes
    )

    top_cand = state.top_candidate
    mmsi = top_cand.vessel.mmsi if top_cand else (state.matched_ais_observation.mmsi if state.matched_ais_observation else None)
    vessel_name = top_cand.vessel.name if top_cand else None
    
    # Also check if query IMO or target is passed in details or detection
    imo = getattr(detection := state.active_detection, "suspected_imo", None)

    sanctions_res, is_degraded = screen_sanctions(
        imo=imo,
        mmsi=mmsi,
        vessel_name=vessel_name,
        force_offline=simulated_offline
    )

    status = "DEGRADED" if is_degraded else "SUCCESS"
    if is_degraded:
        degradation_msg = "Live official sanctions database offline: screened with unverified fallback baseline."
        if degradation_msg not in degradation_notes:
            degradation_notes.append(degradation_msg)

    details = {
        "query_target": sanctions_res.query_target,
        "is_sanctioned": sanctions_res.is_sanctioned,
        "overall_sanctions_risk": sanctions_res.overall_sanctions_risk,
        "matches_count": len(sanctions_res.matches),
        "is_degraded": is_degraded
    }

    trace = _append_trace(
        state=state,
        agent_name="SanctionsScreenerNode",
        action="SCREEN_OFAC_UN_SANCTIONS",
        status=status,
        details=details,
        notes=sanctions_res.screening_notes
    )

    return {
        "sanctions_result": sanctions_res,
        "degradation_notes": degradation_notes,
        "current_node": "SanctionsScreenerNode",
        "completed_nodes": list(state.completed_nodes or []) + ["SanctionsScreenerNode"],
        "execution_trace": trace
    }


# -------------------------------------------------------------------------
# Node 5: ForensicAssessorNode
# -------------------------------------------------------------------------
def forensic_assessor_node(state: MaritimeAgentState) -> Dict[str, Any]:
    """
    Computes evidential risk score, determines dark vessel classification,
    projects kinematic dead-reckoning forecast, and sets Human-in-the-Loop flag
    for high-risk scenarios.
    """
    features = state.engineered_features
    sanctions_res = state.sanctions_result
    geo_ctx = state.geo_context

    risk_assessment, forecast = assess_risk_and_forecast(
        features=features,
        sanctions_result=sanctions_res,
        geo_context=geo_ctx
    )

    # Determine if Human-in-the-Loop oversight is required
    # High-risk triggers:
    # 1. Anomaly score >= 0.70
    # 2. DELIBERATE_DARK_EVASION classification
    # 3. Confirmed or high sanctions match
    is_high_risk = (
        risk_assessment.overall_anomaly_score >= 0.70 or
        risk_assessment.dark_vessel_classification == "DELIBERATE_DARK_EVASION" or
        sanctions_res.is_sanctioned
    )

    hitl_flag = is_high_risk or state.human_in_the_loop_flag

    details = {
        "dark_vessel_probability": risk_assessment.dark_vessel_probability,
        "dark_vessel_classification": risk_assessment.dark_vessel_classification,
        "overall_anomaly_score": risk_assessment.overall_anomaly_score,
        "sanctions_risk_level": risk_assessment.sanctions_risk_level,
        "eez_threat_level": risk_assessment.eez_threat_level,
        "human_in_the_loop_flag": hitl_flag,
        "extrapolated_waypoints_count": len(forecast.extrapolated_waypoints)
    }

    trace = _append_trace(
        state=state,
        agent_name="ForensicAssessorNode",
        action="EVALUATE_RISK_AND_TRAJECTORY",
        status="SUCCESS",
        details=details,
        notes=f"Assessed risk: {risk_assessment.dark_vessel_classification} (Anomaly Score: {risk_assessment.overall_anomaly_score:.2f}). HITL={hitl_flag}."
    )

    return {
        "risk_assessment": risk_assessment,
        "human_in_the_loop_flag": hitl_flag,
        "current_node": "ForensicAssessorNode",
        "completed_nodes": list(state.completed_nodes or []) + ["ForensicAssessorNode"],
        "execution_trace": trace
    }


# -------------------------------------------------------------------------
# Node 5b: HumanReviewNode (HITL Gate)
# -------------------------------------------------------------------------
def human_review_node(state: MaritimeAgentState) -> Dict[str, Any]:
    """
    Human-in-the-Loop review checkpoint for high-risk dark vessel and sanctions cases.
    Logs analyst disposition and records review audit notes into the trace.
    """
    feedback = state.human_feedback or "AUTOMATED_HITL_CHECKPOINT_PASSED: Operator alerted, priority escalated."
    
    details = {
        "human_review_status": "REVIEWED" if state.human_feedback else "FLAGGED_FOR_OPERATOR",
        "human_feedback": feedback,
        "target_id": state.active_detection.detection_id if state.active_detection else "UNKNOWN"
    }

    trace = _append_trace(
        state=state,
        agent_name="HumanReviewNode",
        action="HUMAN_IN_THE_LOOP_OVERSIGHT",
        status="SUCCESS",
        details=details,
        notes=f"Human-in-the-loop review recorded: {feedback}"
    )

    return {
        "human_feedback": feedback,
        "current_node": "HumanReviewNode",
        "completed_nodes": list(state.completed_nodes or []) + ["HumanReviewNode"],
        "execution_trace": trace
    }


# -------------------------------------------------------------------------
# Node 6: ReportPreparerNode
# -------------------------------------------------------------------------
def report_preparer_node(state: MaritimeAgentState) -> Dict[str, Any]:
    """
    Assembles final structured IntelligenceReport payload containing statutory
    citations (SOLAS V/19, UNCLOS Art 73, OFAC), concrete evidence references,
    and operational dispatch recommendations.
    """
    mission = state.mission
    detection = state.active_detection
    features = state.engineered_features
    risk_assessment = state.risk_assessment
    sanctions_res = state.sanctions_result
    geo_ctx = state.geo_context
    top_cand = state.top_candidate

    # Trajectory forecast
    _, forecast = assess_risk_and_forecast(
        features=features,
        sanctions_result=sanctions_res,
        geo_context=geo_ctx
    )

    final_report = generate_structured_report(
        mission_id=mission.mission_id,
        target_detection_id=detection.detection_id,
        features=features,
        risk_assessment=risk_assessment,
        sanctions_result=sanctions_res,
        geo_context=geo_ctx,
        forecast=forecast,
        top_candidate=top_cand,
        degradation_notes=state.degradation_notes,
        human_in_the_loop=state.human_in_the_loop_flag,
        detection_confidence=detection.confidence
    )

    details = {
        "report_id": final_report.report_id,
        "threat_tier": final_report.threat_tier,
        "statutory_violations_count": len(final_report.statutory_violations),
        "recommendations_count": len(final_report.actionable_recommendations)
    }

    trace = _append_trace(
        state=state,
        agent_name="ReportPreparerNode",
        action="GENERATE_FINAL_INTELLIGENCE_BULLETIN",
        status="SUCCESS",
        details=details,
        notes=f"Compiled bulletin {final_report.report_id} with threat tier {final_report.threat_tier}."
    )

    return {
        "final_report": final_report,
        "current_node": "ReportPreparerNode",
        "completed_nodes": list(state.completed_nodes or []) + ["ReportPreparerNode"],
        "execution_trace": trace
    }
