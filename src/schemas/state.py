"""LangGraph Agent State schema representing Pillar 2 of the project evaluation.
Carries typed state, multi-source evidence, agent execution logs, and graceful
degradation notes across the agentic graph.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from src.schemas.mission import Mission
from src.schemas.sar import SARDetection, SARScene
from src.schemas.ais import AISObservation, AISGap
from src.schemas.vessel import VesselCandidate
from src.schemas.geospatial import GeoContext
from src.schemas.sanctions import SanctionsResult
from src.schemas.features import EngineeredFeatures
from src.schemas.intelligence import RiskAssessment, IntelligenceReport

class AgentTraceEntry(BaseModel):
    step_number: int
    agent_name: str
    action_taken: str
    status: str = Field(default="SUCCESS", description="SUCCESS, DEGRADED, FAILED, SKIPPED")
    details: Dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = None

class MaritimeAgentState(BaseModel):
    """The central state container flowing through all LangGraph agents."""
    mission: Mission
    current_node: str = Field(default="controller", description="Currently executing agent node")
    completed_nodes: List[str] = Field(default_factory=list)
    
    # Sensor & Registry Evidence
    sar_scene: Optional[SARScene] = None
    all_detections: List[SARDetection] = Field(default_factory=list)
    active_detection: Optional[SARDetection] = None
    
    # Correlated Tracking Data
    matched_ais_observation: Optional[AISObservation] = None
    historical_gaps: List[AISGap] = Field(default_factory=list)
    
    # Attribution & Spatial Data
    geo_context: Optional[GeoContext] = None
    identity_candidates: List[VesselCandidate] = Field(default_factory=list)
    top_candidate: Optional[VesselCandidate] = None
    sanctions_result: Optional[SanctionsResult] = None
    
    # Feature Engineering (Pillar 1)
    engineered_features: Optional[EngineeredFeatures] = None
    
    # Statistical / ML Risk Assessment
    risk_assessment: Optional[RiskAssessment] = None
    
    # Fine-Tuned LLM Output (Pillar 3)
    final_report: Optional[IntelligenceReport] = None
    
    # Resilience, Degradation & Human-in-the-Loop
    degradation_notes: List[str] = Field(
        default_factory=list,
        description="Records if an agent lacked data (e.g. AIS unavailable) and degraded gracefully"
    )
    human_in_the_loop_flag: bool = Field(default=False)
    human_feedback: Optional[str] = None
    execution_trace: List[AgentTraceEntry] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
