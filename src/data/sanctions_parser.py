"""Official Sanctions Parser & Screening Engine.
Parses real U.S. OFAC SDN and UN Security Council Consolidated XML files.
Indexes sanctioned maritime vessels by IMO, MMSI, and Vessel Name for instant sub-millisecond screening.
"""

import os
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple
from src.schemas.sanctions import SanctionMatch, SanctionsResult
from src.utils.logger import setup_logger

logger = setup_logger("sanctions_parser")

class RealSanctionsDatabase:
    """In-memory indexed database of real OFAC & UN sanctioned vessels."""

    def __init__(self, ofac_xml_path: str = "data/raw/sanctions/sdn.xml", un_xml_path: str = "data/raw/sanctions/un_consolidated.xml"):
        self.ofac_xml_path = ofac_xml_path
        self.un_xml_path = un_xml_path
        
        # Primary lookup indices
        self.by_imo: Dict[str, List[SanctionMatch]] = {}
        self.by_mmsi: Dict[str, List[SanctionMatch]] = {}
        self.by_name: Dict[str, List[SanctionMatch]] = {}
        self.total_vessels_indexed = 0

        self._load_and_index()

    @staticmethod
    def _normalize_str(s: str) -> str:
        """Removes punctuation and normalizes string for robust matching."""
        if not s:
            return ""
        return re.sub(r"[^A-Z0-9]", "", s.upper())

    def _extract_imo(self, text: str) -> Optional[str]:
        """Extracts 7-digit IMO number from text."""
        match = re.search(r"\b(\d{7})\b", text)
        return match.group(1) if match else None

    def _index_match(self, match: SanctionMatch):
        """Adds a match record into the lookup indices."""
        self.total_vessels_indexed += 1
        if match.matched_imo:
            clean_imo = match.matched_imo.strip()
            self.by_imo.setdefault(clean_imo, []).append(match)
        if match.matched_mmsi:
            clean_mmsi = match.matched_mmsi.strip()
            self.by_mmsi.setdefault(clean_mmsi, []).append(match)
        norm_name = self._normalize_str(match.entity_name)
        if norm_name:
            self.by_name.setdefault(norm_name, []).append(match)

    def _load_ofac(self):
        """Parses real U.S. OFAC SDN XML."""
        if not os.path.exists(self.ofac_xml_path):
            logger.warning(f"OFAC XML file not found at {self.ofac_xml_path}")
            return

        logger.info(f"Parsing real OFAC SDN XML from {self.ofac_xml_path}...")
        tree = ET.parse(self.ofac_xml_path)
        root = tree.getroot()
        ns = {'ofac': 'https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/XML'}

        count = 0
        for entry in root.findall('.//ofac:sdnEntry', ns):
            sdn_type = entry.find('ofac:sdnType', ns)
            remarks = entry.find('ofac:remarks', ns)
            remarks_text = remarks.text if remarks is not None and remarks.text else ""
            
            # Determine if this is a maritime vessel
            is_vessel = (sdn_type is not None and sdn_type.text == 'Vessel') or ('vessel' in remarks_text.lower())
            if not is_vessel:
                continue

            name_elem = entry.find('ofac:lastName', ns)
            entity_name = name_elem.text if name_elem is not None and name_elem.text else "UNKNOWN VESSEL"

            # Programs (e.g. IRAN, RUSSIA-EO14024)
            prog_elem = entry.find('ofac:programList', ns)
            programs = [p.text for p in prog_elem.findall('ofac:program', ns)] if prog_elem is not None else []

            # Extract IDs (IMO, MMSI, Call Sign, Flag)
            matched_imo = None
            matched_mmsi = None
            callsign = None
            flag = None

            id_list = entry.find('ofac:idList', ns)
            if id_list is not None:
                for id_item in id_list.findall('ofac:id', ns):
                    id_type = (id_item.find('ofac:idType', ns).text or '').lower() if id_item.find('ofac:idType', ns) is not None else ''
                    id_val = (id_item.find('ofac:idNumber', ns).text or '') if id_item.find('ofac:idNumber', ns) is not None else ''

                    if 'vessel registration' in id_type or 'imo' in id_type or 'imo' in id_val.lower():
                        extracted = self._extract_imo(id_val)
                        if extracted:
                            matched_imo = extracted
                    elif 'mmsi' in id_type:
                        matched_mmsi = id_val.strip()
                    elif 'call sign' in id_type:
                        callsign = id_val.strip()
                    elif 'flag' in id_type:
                        flag = id_val.strip()

            # Also check remarks if IMO wasn't in idList
            if not matched_imo and 'imo' in remarks_text.lower():
                matched_imo = self._extract_imo(remarks_text)

            match = SanctionMatch(
                source_list="OFAC_SDN",
                entity_name=entity_name,
                entity_type="VESSEL",
                matched_imo=matched_imo,
                matched_mmsi=matched_mmsi,
                matched_callsign=callsign,
                flag_state=flag,
                sanction_programs=programs,
                match_score=1.0,
                match_basis="OFFICIAL_OFAC_DESIGNATION",
                remarks=remarks_text[:200] if remarks_text else None
            )
            self._index_match(match)
            count += 1

        logger.info(f"Loaded {count} real OFAC sanctioned vessels into index.")

    def _load_un(self):
        """Parses real UN Security Council Consolidated XML."""
        if not os.path.exists(self.un_xml_path):
            logger.warning(f"UN XML file not found at {self.un_xml_path}")
            return

        logger.info(f"Parsing real UN Consolidated Sanctions XML from {self.un_xml_path}...")
        try:
            tree = ET.parse(self.un_xml_path)
            root = tree.getroot()
            count = 0
            for entity in root.findall('.//ENTITIES/ENTITY'):
                name_elem = entity.find('FIRST_NAME')
                name = name_elem.text if name_elem is not None and name_elem.text else ""
                comments = entity.find('COMMENTS1')
                comm_text = comments.text if comments is not None and comments.text else ""
                
                # Check for vessel keywords or IMO
                if 'vessel' in comm_text.lower() or 'imo' in comm_text.lower() or 'tanker' in comm_text.lower():
                    imo = self._extract_imo(comm_text)
                    match = SanctionMatch(
                        source_list="UN_CONSOLIDATED",
                        entity_name=name,
                        entity_type="VESSEL",
                        matched_imo=imo,
                        match_score=1.0,
                        match_basis="OFFICIAL_UN_SANCTION",
                        remarks=comm_text[:200] if comm_text else None
                    )
                    self._index_match(match)
                    count += 1
            logger.info(f"Loaded {count} real UN sanctioned vessels into index.")
        except Exception as e:
            logger.error(f"Error parsing UN XML: {e}")

    def _load_and_index(self):
        self._load_ofac()
        self._load_un()
        logger.info(f"Total Sanctions Index: {self.total_vessels_indexed} vessels ({len(self.by_imo)} unique IMOs, {len(self.by_mmsi)} MMSIs)")

    def screen_vessel(
        self,
        imo: Optional[str] = None,
        mmsi: Optional[str] = None,
        vessel_name: Optional[str] = None
    ) -> SanctionsResult:
        """
        Screens a query vessel against real OFAC & UN sanctions indices.
        Returns a strongly typed SanctionsResult object.
        """
        query_key = imo or mmsi or vessel_name or "UNKNOWN"
        matches: List[SanctionMatch] = []

        # 1. Exact IMO match (Highest confidence: 1.0)
        if imo:
            clean_imo = self._extract_imo(str(imo)) or str(imo).strip()
            if clean_imo in self.by_imo:
                for m in self.by_imo[clean_imo]:
                    m_copy = m.model_copy()
                    m_copy.match_score = 1.0
                    m_copy.match_basis = f"EXACT_IMO_MATCH ({clean_imo})"
                    matches.append(m_copy)

        # 2. Exact MMSI match (Confidence: 0.95)
        if mmsi and not matches:
            clean_mmsi = str(mmsi).strip()
            if clean_mmsi in self.by_mmsi:
                for m in self.by_mmsi[clean_mmsi]:
                    m_copy = m.model_copy()
                    m_copy.match_score = 0.95
                    m_copy.match_basis = f"EXACT_MMSI_MATCH ({clean_mmsi})"
                    matches.append(m_copy)

        # 3. Exact Normalized Name match (Confidence: 0.85)
        if vessel_name and not matches:
            norm_name = self._normalize_str(vessel_name)
            if norm_name in self.by_name:
                for m in self.by_name[norm_name]:
                    m_copy = m.model_copy()
                    m_copy.match_score = 0.85
                    m_copy.match_basis = f"EXACT_NAME_MATCH ({vessel_name.strip().upper()})"
                    matches.append(m_copy)

        is_hit = len(matches) > 0
        overall_risk = "CONFIRMED" if (is_hit and matches[0].match_score >= 0.95) else ("HIGH" if is_hit else "CLEAN")

        notes = None
        if is_hit:
            programs = [p for m in matches for p in m.sanction_programs]
            notes = f"Designated under {', '.join(set(programs)) if programs else 'Maritime Watchlist'}."

        return SanctionsResult(
            query_target=query_key,
            is_sanctioned=is_hit,
            overall_sanctions_risk=overall_risk,
            matches=matches,
            screened_sources=["OFAC_SDN", "UN_CONSOLIDATED"],
            screening_notes=notes
        )
