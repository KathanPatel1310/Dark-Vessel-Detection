# Data Sources & Ingestion Architecture

## 1. Multi-Source Ingestion Strategy

The platform integrates multi-modal remote sensing, transponder telemetry, and international compliance databases into a unified, high-throughput analytical pipeline. To maximize query speed and avoid redundant I/O bottlenecks, data ingestion is partitioned into specialized streaming and column-optimized formats:

### Dataset Specifications & Pipeline Roles

| Resource Name | Category | Primary Format | Ingestion Method | Pipeline Role |
| :--- | :--- | :--- | :--- | :--- |
| **Real AIS Vessel Trajectories** | Vessel Telemetry | Snappy GeoParquet | Streamed Columnar Ingestion | High-density kinematics, trajectory curvature, and transmission gap forensics |
| **Real Sentinel-1 SAR Detections** | Remote Sensing | Vector CSV | Analysis-Ready Extraction | Target dimensions, radar backscatter statistics, and ground-truth dark flags |
| **U.S. OFAC SDN Sanctions List** | Sanctions Compliance | Stream-Indexed XML | Automated REST Retrieval | Authoritative government designation matching by IMO, MMSI, and name |
| **UN Consolidated Sanctions** | Sanctions Compliance | Stream-Indexed XML | Direct HTTPS Pull | Global Security Council blacklisted vessel screening |
| **UNCLOS Sovereign EEZ Boundaries** | Maritime Geography | GeoJSON Polygons | Spatial Point-in-Polygon | Legal territorial boundary checks and jurisdictional threat assessment |
| **SSDD SAR Ship Benchmark** | Computer Vision | XML / JPEG Chips | Local High-Speed Cache | Radar bounding-box and dimension estimation validation |
| **Qwen2.5 (3B / 7B) Foundation Weights** | Language Model | 4-bit NF4 Safetensors | Hugging Face Hub Engine | Supervised Fine-Tuning (QLoRA) for structured intelligence report generation |

---

## 2. Ingested Production Data Assets

### 2.1 Sanctions Watchlists
1.  **U.S. OFAC Specially Designated Nationals (SDN) List:**
    *   *URL:* `https://www.treasury.gov/ofac/downloads/sdn_xml.zip`
    *   *Fields Ingested:* `uid`, `lastName` (Vessel Name), `sdnType`, `programList` (e.g. `IRAN`, `RUSSIA-EO14024`), `idList` (IMO number, MMSI, Callsign, Flag State), and `remarks`.
    *   *Indexing:* In-memory hash indexing by 7-digit IMO and 9-digit MMSI for < 1 ms query latency.
2.  **UN Security Council Consolidated Sanctions List:**
    *   *URL:* `https://scsanctions.un.org/resources/xml/en/consolidated.xml`
    *   *Fields Ingested:* Entity identity, vessel registration numbers, and UN resolution citations.

---

### 2.2 Vessel Tracking & AIS Trajectory Streams
1.  **High-Volume Commercial AIS Stream (`real_ais_traffic.parquet`):**
    *   *Fields Ingested:* `MMSI`, `BaseDateTime`, `LAT`, `LON`, `SOG` (Speed Over Ground), `COG` (Course Over Ground), `Heading`, `VesselName`, `IMO`, `CallSign`, `VesselType`, `Status`, `Length`, `Width`, `Draft`.
    *   *Performance:* Snappy-compressed columnar Parquet enabling vector queries over 100,000+ pings in milliseconds.
2.  **Global Fishing Watch (GFW) 4Wings & SAR API:**
    *   *Endpoint:* `public-global-sar-presence:latest`
    *   *Fields:* `detection_id`, `timestamp`, `latitude`, `longitude`, `matched` (boolean AIS correlation), `length_m`, `neural_vessel_type`, `presence_score`.

---

### 2.3 Maritime Geospatial & EEZ Boundaries
1.  **Exclusive Economic Zone (EEZ) Polygons:**
    *   *Source:* Flanders Marine Institute (VLIZ) Marine Regions / UNCLOS Official Filings.
    *   *Scope:* Indian Ocean, Arabian Sea, Gulf of Oman, and Persian Gulf.
    *   *Geometry:* High-precision polygons defining territorial seas, contiguous zones, and sovereign EEZ borders.
2.  **Designated High-Risk Corridors & STS Zones:**
    *   *Source:* IMO / UNODC Designated Maritime Security Zones (Fujairah offshore anchorage, Gulf of Oman evasion sector, Central Arabian Sea corridor).

---

### 2.4 Domain Fine-Tuning Corpus (Planned Phase 4)
*   **Corpus Architecture:** Paired instruction-tuning examples mapping fused feature vectors directly to standardized maritime intelligence bulletins.
*   **Ground Truth Sources:**
    1.  UNODC Global Maritime Crime Programme published investigation reports.
    2.  IMO Maritime Safety Committee circulars (SOLAS Chapter V enforcement).
    3.  US Coast Guard and IFC-IOR maritime security advisories.
    4.  OFAC Maritime Sanctions Advisories on deceptive shipping practices.
