from typing import List, Optional
from pydantic import BaseModel, Field

class VesselIdentity(BaseModel):
    imo: Optional[str] = Field(None, description="IMO number")
    mmsi: Optional[str] = Field(None, description="MMSI number")
    name: str = Field(..., description="Vessel official registered name")
    callsign: Optional[str] = Field(None, description="Radio callsign")
    flag: Optional[str] = Field(None, description="Flag of registry (e.g. Panama, Liberia, Iran)")
    vessel_type: Optional[str] = Field(None, description="Crude Oil Tanker, Bulk Carrier, Fishing Vessel, etc.")
    built_year: Optional[int] = Field(None, ge=1900, le=2030)
    length_overall_m: Optional[float] = Field(None, ge=0.0, description="Registered Length Overall (LOA)")
    beam_m: Optional[float] = Field(None, ge=0.0, description="Registered Beam/Width")
    gross_tonnage: Optional[float] = Field(None, ge=0.0)
    deadweight_tonnage: Optional[float] = Field(None, ge=0.0)
    owner_name: Optional[str] = Field(None, description="Registered owning entity")
    operator_name: Optional[str] = Field(None, description="Commercial operator")
    beneficial_owner_country: Optional[str] = Field(None)

class VesselCandidate(BaseModel):
    vessel: VesselIdentity
    match_confidence: float = Field(..., ge=0.0, le=1.0, description="Overall matching confidence score")
    dimension_similarity: float = Field(..., ge=0.0, le=1.0, description="Compatibility between SAR length/beam and registry")
    route_plausibility: float = Field(..., ge=0.0, le=1.0, description="Plausibility based on prior AIS trajectory")
    provenance_source: str = Field(default="ITU_MARS", description="Source: GFW_API, ITU_MARS, IMO_GISIS, MOCK_REGISTRY")
    matching_rationale: str = Field(..., description="Explanation of why this candidate was retrieved and scored")
