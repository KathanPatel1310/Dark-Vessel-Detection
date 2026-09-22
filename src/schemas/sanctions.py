from typing import List, Optional
from pydantic import BaseModel, Field

class SanctionMatch(BaseModel):
    source_list: str = Field(..., description="Sanctions list origin (e.g. OFAC_SDN, UN_CONSOLIDATED, EU_SANCTIONS)")
    entity_name: str = Field(..., description="Registered or designated entity/vessel name")
    entity_type: str = Field(default="VESSEL", description="VESSEL, INDIVIDUAL, or CORPORATE_OWNER")
    matched_imo: Optional[str] = None
    matched_mmsi: Optional[str] = None
    matched_callsign: Optional[str] = None
    flag_state: Optional[str] = None
    sanction_programs: List[str] = Field(default_factory=list, description="Sanctions authorities (e.g. ['IRAN-EO13846', 'RUSSIA-EO14024'])")
    designation_date: Optional[str] = None
    match_score: float = Field(..., ge=0.0, le=1.0, description="Confidence of the match (1.0 = exact IMO match)")
    match_basis: str = Field(..., description="Method of match (EXACT_IMO, EXACT_MMSI, FUZZY_NAME, ALIAS)")
    remarks: Optional[str] = None

class SanctionsResult(BaseModel):
    query_target: str = Field(..., description="IMO, MMSI, or vessel name queried")
    is_sanctioned: bool = Field(default=False, description="True if one or more confirmed matches exist")
    overall_sanctions_risk: str = Field(default="CLEAN", description="Risk tier: CLEAN, SUSPICIOUS, HIGH, CONFIRMED")
    matches: List[SanctionMatch] = Field(default_factory=list)
    screened_sources: List[str] = Field(default_factory=lambda: ["OFAC_SDN", "UN_CONSOLIDATED"])
    screening_notes: Optional[str] = None
