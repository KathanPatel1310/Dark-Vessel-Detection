# Data Sources & Storage Footprint Budget

## 1. Storage Budget & Safe Download Policy

> [!IMPORTANT]
> **Strict Storage Preservation Rule:** No external dataset, model weight, or large archive is downloaded automatically. All data requirements are audited in advance. The table below outlines the exact storage footprints to allow the user to select the appropriate footprint tier based on available hard drive space.

### Prospective Resource Storage Footprints

| Resource Name | Category | Exact / Est. Storage | Access Method | Project Tier Recommendation | Current Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Synthetic Test Fixtures** | Testing / Fixtures | **< 100 KB** | Built-in Python generator (`src/data/mock_generator.py`) | **Tier 1 (Mandatory Baseline)** | **Created & Ready** |
| **OFAC SDN Compressed List** | Sanctions | **~15 MB** (zip) | Direct HTTPS download from US Treasury | **Tier 1 (Recommended)** | Ready for Phase 2 |
| **UN Consolidated Sanctions** | Sanctions | **~2 MB** (xml) | Direct HTTPS download from UN Security Council | **Tier 1 (Recommended)** | Ready for Phase 2 |
| **SSDD Benchmark Dataset** | SAR Benchmark | **~35 MB** | GitHub repository release | **Tier 1 (Recommended for CV test)** | Optional for Phase 2 |
| **MarineRegions EEZ (India/Arabian Sea)** | Geospatial Boundaries | **< 2 MB** (GeoJSON) | Curated coastal/EEZ coordinates or Marine Regions download | **Tier 1 (Recommended)** | Ready for Phase 2 |
| **Qwen2.5-3B-Instruct (4-bit QLoRA)** | LLM Weights | **~2.0 GB** | Hugging Face Hub (`bitsandbytes` 4-bit) | **Tier 1 (Ultra-low storage fine-tuning)** | For Phase 4 |
| **Qwen2.5-7B-Instruct (4-bit QLoRA)** | LLM Weights | **~4.5 GB** | Hugging Face Hub (`bitsandbytes` 4-bit) | **Tier 2 (Standard research fine-tuning)** | For Phase 4 |
| **HRSID Dataset** | High-Res SAR | **~850 MB** | Kaggle / GitHub archive | Tier 2 (Optional high-res CV benchmark) | Not downloaded |
| **OpenSARShip Dataset** | SAR-AIS Chips | **~1.5 GB** | OpenSAR SJTU portal | Tier 2 (Optional dimension validation) | Not downloaded |
| **OpenSanctions Bulk Dump** | Sanctions | **2.42 GB** | OpenSanctions FTM export | **Tier 3 (AVOID - Use OFAC 15MB instead)** | Excluded |
| **Full Sentinel-1 GRD Scene** | Satellite Raw | **1.2 - 1.6 GB per scene** | Copernicus Data Space Ecosystem | **Tier 3 (AVOID - Use GFW API / chips)** | Excluded |
| **xView3 Full Raw Archive** | Large-scale SAR | **> 1,000 GB (1 TB)** | xView3 IUU challenge portal | **Tier 3 (AVOID - Use annotations only)** | Excluded |

---

## 2. Planned Production Data Sources

### 2.1 Sanctions Lists (Tier 1: ~17 MB Total)
1.  **OFAC Specially Designated Nationals (SDN) List:**
    *   *URL:* `https://www.treasury.gov/ofac/downloads/sdn_xml.zip`
    *   *Fields Required:* Entity Name, Entity Type, Vessel IMO, Vessel MMSI, Callsign, Flag State, Sanctions Program (e.g. `IRAN`, `RUSSIA-EO14024`).
    *   *Format:* XML.
    *   *Storage:* ~15 MB compressed.
2.  **UN Security Council Consolidated Sanctions List:**
    *   *URL:* `https://www.un.org/securitycouncil/content/un-sc-consolidated-list`
    *   *Fields Required:* Individual/Entity identity, vessel identifiers, UN resolution references.
    *   *Format:* XML.
    *   *Storage:* ~2 MB.

---

### 2.2 Vessel Tracking & AIS Gaps (Tier 1: < 50 MB / API Streaming)
1.  **Global Fishing Watch (GFW) 4Wings & SAR API:**
    *   *Endpoint:* `public-global-sar-presence:latest`
    *   *Fields Required:* `detection_id`, `timestamp`, `latitude`, `longitude`, `matched` (boolean AIS match), `length_m`, `neural_vessel_type`, `presence_score`.
    *   *Method:* HTTPS REST API using academic access token (no large bulk download needed; queries execute on-demand per bounding box).
    *   *Storage:* Streamed JSON responses (< 5 MB per session).
2.  **Synthetic & Pre-extracted AIS Feeds:**
    *   *Fields Required:* MMSI, IMO, Vessel Name, SOG, COG, Draught, Lat, Lon, Timestamp, Gap Start/End.
    *   *Storage:* ~1-10 MB JSON/CSV in `data/fixtures/` and `data/processed/`.

---

### 2.3 Maritime Geospatial & EEZ Boundaries (Tier 1: < 5 MB)
1.  **Exclusive Economic Zone (EEZ) Polygons:**
    *   *Source:* Marine Regions (Flanders Marine Institute) v12 / Natural Earth Maritime Boundaries.
    *   *Scope:* Filtered specifically for the Western Indian Ocean & Arabian Sea (India, Oman, Pakistan, Yemen, international waters).
    *   *Fields Required:* Sovereign state name, EEZ polygon coordinates, treaty zone indicators.
    *   *Storage:* ~1.5 MB GeoJSON.
2.  **High-Risk Shipping Corridors & STS Zones:**
    *   *Source:* Curated geographic risk centroids (Gulf of Oman approach, Fujairah offshore anchorage, Western India EEZ boundary line).
    *   *Storage:* < 100 KB JSON config.

---

### 2.4 LLM Fine-Tuning Corpus (Tier 1: < 5 MB)
*   **Corpus Description:** Formatted instruction-tuning pairs combining input feature vectors with expert-style maritime intelligence narratives.
*   **Sources of Domain Knowledge:**
    1.  UNODC Global Maritime Crime Programme published bulletins.
    2.  IMO Maritime Safety Committee circulars (SOLAS Chapter V guidelines).
    3.  US Coast Guard and IFC-IOR maritime security advisories.
    4.  OFAC Maritime Sanctions Advisories (identifying ship-to-ship transfer evasion tactics).
*   **Dataset Size:** 400 - 1,000 structured JSONL examples.
*   **Storage Footprint:** **~3.5 MB JSONL**.
