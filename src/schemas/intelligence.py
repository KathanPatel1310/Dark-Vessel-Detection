"""Schemas for analytical risk assessments and final structured intelligence reports.
Represents the target domain generation format of the Fine-Tuned LLM (Pillar 3).
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class TrajectoryPoint(BaseModel):
    projection_hours: float = Field(..., description="Hours into future (e.g. +6, +12, +24)")
    projected_lat: float = Field(..., ge=-90.0, le=90.0)
    projected_lon: float = Field(..., ge=-180.0, le=180.0)
    uncertainty_radius_km: float = Field(..., ge=0.0, description="Error cone radius")
    projected_timestamp: datetime

class PredictiveForecast(BaseModel):
    extrapolated_waypoints: List[TrajectoryPoint] = Field(default_factory=list)
    projected_eez_incursion: bool = Field(default=False)
    projected_eez_eta_hours: Optional[float] = None
    projected_activity: Optional[str] = Field(None, description="e.g. STS Rendezvous, Port Entry, Incursion")
    forecast_confidence: float = Field(..., ge=0.0, le=1.0)
    methodology_notes: str = Field(..., description="Explanation of kinematic or routing assumptions")

class RiskAssessment(BaseModel):
    dark_vessel_probability: float = Field(..., ge=0.0, le=1.0, description="Probability that absence of AIS is deliberate evasion")
    dark_vessel_classification: str = Field(
        ...,
        description="Category: DELIBERATE_DARK_EVASION, SMALL_CRAFT_EXEMPT, AIS_SHADOW_ZONE, SPOOFING_ANOMALY, CORRELATED_BENIGN"
    )
    sanctions_risk_level: str = Field(default="CLEAN", description="CLEAN, LOW, ELEVATED, HIGH, CRITICAL")
    eez_threat_level: str = Field(default="NONE", description="NONE, LOW, MODERATE, HIGH, CRITICAL")
    overall_anomaly_score: float = Field(..., ge=0.0, le=1.0)
    risk_factors: List[str] = Field(default_factory=list, description="Specific triggers elevating the risk")

class IntelligenceReport(BaseModel):
    report_id: str = Field(..., description="Unique intelligence bulletin ID (e.g. MAR-INTEL-2026-0042)")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    mission_id: str
    target_detection_id: str
    
    # Executive Summary
    executive_summary: str = Field(..., description="High-level analyst summary synthesized by the fine-tuned LLM")
    threat_tier: str = Field(..., description="LOW, MEDIUM, HIGH, SEVERE")
    
    # Detailed Analytical Sections
    vessel_characteristics_summary: str = Field(..., description="Derived length, beam, estimated class from SAR")
    ais_status_summary: str = Field(..., description="Analysis of transmission history, last known ping, gap duration")
    identity_attribution_summary: str = Field(..., description="Candidate vessel identity, flags, owner, and confidence")
    sanctions_findings: str = Field(..., description="Screening results against OFAC SDN, UN, and EU registries")
    geospatial_eez_analysis: str = Field(..., description="Proximity to EEZ boundaries, territorial waters, and sensitive zones")
    
    # Predictive Forecast (Kinematic / Analytical)
    predictive_forecast: PredictiveForecast
    
    # Legal & Operational Output
    statutory_violations: List[str] = Field(
        default_factory=list,
        description="Relevant statutes cited (e.g. SOLAS Ch. V Reg. 19, UNCLOS Art. 73, OFAC Iranian Sanctions)"
    )
    actionable_recommendations: List[str] = Field(
        default_factory=list,
        description="Recommended procedural actions (e.g. File IFC-IOR bulletin, Coast Guard aerial patrol dispatch)"
    )
    analyst_confidence_statement: str = Field(..., description="Explicit disclaimer of sensor limitations and confidence bounds")
