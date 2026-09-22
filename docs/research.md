# Comprehensive Research & Technology Audit

## 1. Critical Audit of Original Project Documentation (PDF)

The original project document (*"Dark Vessel Detection & Maritime Intelligence System"*) proposed a high-level conceptual vision for maritime surveillance. However, an in-depth technical examination reveals several critical inaccuracies, outdated dependencies, and overly ambitious claims that must be reformed for a credible academic prototype.

| Component / Claim in PDF | Status | Technical Reality & Flaw | Action in Redesigned Architecture |
| :--- | :--- | :--- | :--- |
| **sentinelsat & Copernicus Open Access Hub** | **Obsolete / Broken** | ESA permanently decommissioned the Copernicus Open Access Hub (SciHub) on **October 31, 2023**. The `sentinelsat` library is no longer maintained for new Copernicus access. | **Replaced:** Use Copernicus Data Space Ecosystem (CDSE) APIs (STAC/OData), Global Fishing Watch 4Wings API, or pre-extracted benchmark scenes. |
| **"SAR detected + no AIS = Dark Vessel"** | **Technically Flawed** | Naive assumption. Small artisanal fishing vessels, wooden dhows, and pleasure craft (<300 GT) are legally exempt from AIS under IMO SOLAS V/19. Furthermore, satellite AIS reception in high-density corridors suffers from RF packet collision (message loss), and sea clutter can cause radar false alarms. | **Replaced:** Multi-feature evidential scoring. Features like target length (>50m), clutter ratio, Doppler consistency, and corridor risk must distinguish deliberate dark activity from small craft or coverage shadow zones. |
| **Two-Stage VLM Fine-Tuning (LLaVA-1.6 / InternVL2)** | **Architecturally Inefficient** | Attempting to use a 7B/8B natural image Vision-Language Model (LLaVA) to directly classify single-ship radar chips is deeply flawed. Radar chips are complex microwave backscatter matrices, not RGB photographs. Moreover, using a VLM for textual intelligence report generation causes excessive compute overhead and high risk of hallucination. | **Replaced:** Decoupled Architecture. Use a specialized computer vision / SAR feature extractor (or pretrained YOLO/CFAR features) for target characteristics, then feed structured numerical and textual features into a fine-tuned reasoning LLM (Qwen 2.5 7B/3B). |
| **Autonomous Retraining with Airflow & Evidently AI** | **Over-engineered / Infeasible** | Setting up Apache Airflow, continuous streaming satellite pipelines, Evidently drift monitors, and autonomous self-retraining loops in an academic prototype introduces massive devops fragility, disk usage, and compute waste without advancing the core academic evaluation. | **Removed:** Replaced with lightweight, modular Python pipeline scripts and clear offline evaluation and drift detection baselines. |
| **Predicting Vessel Identity from Dimensions Alone** | **Overstated Claim** | Thousands of global merchant vessels share nearly identical lengths and beams (e.g. standard Panamax or Supramax hulls). Claiming high confidence identity from radar length alone is scientifically invalid. | **Replaced:** Probabilistic candidate ranking. Combines SAR dimensions with last known AIS course, speed plausibility, flag-risk heuristics, and route history to produce a ranked list of candidates with explicit uncertainty bounds. |
| **"Intercept Window" and Tactical Recommendations** | **Operationally Unrealistic** | Real naval/coast guard dispatch involves classified patrol schedules, weather sea-states, and jurisdiction boundaries. Generating rigid military tactical commands from satellite latency (hours old) is unrealistic for an academic AI project. | **Replaced:** Evidence-grounded regulatory and investigative bulletins (referencing UNCLOS, SOLAS, and OFAC/UN sanctions frameworks) suitable for fusion centers like IFC-IOR. |
| **Claims of "First Such System" & IEEE TGRS Target** | **Unsubstantiated** | Organizations like Global Fishing Watch, Spire, Planet, and academic remote sensing groups have published extensive SAR-AIS fusion systems (e.g., xView3 Challenge, 2022). | **Reframed:** The genuine academic contribution is the combination of **granular maritime feature engineering**, **resilient multi-agent reasoning (LangGraph)**, and **QLoRA fine-tuning of an open-weight LLM** for structured intelligence reporting. |

---

## 2. Research Findings by Key Domain

### 2.1 Global Fishing Watch (GFW)
*   **APIs:** GFW provides the **4Wings API** and **Events API**, accessible via the open-source `gfw-api-python-client`.
*   **SAR Presence Dataset:** The dataset `public-global-sar-presence:latest` contains industrial vessel detections derived from Sentinel-1 from 2017 to within ~5 days of real-time. Crucially, GFW pre-computes whether each SAR detection is matched to an AIS transmission (`matched: true/false`), vessel length, and neural vessel classifications (`Likely Fishing`, `Likely Non-Fishing`).
*   **Academic Access:** Free access tokens are readily available for academic and non-commercial research upon registration, with generous monthly query rate limits.

### 2.2 Copernicus Data Space Ecosystem (CDSE)
*   **Current State:** CDSE (dataspace.copernicus.eu) is ESA's sole official portal for Sentinel data. Access is governed via modern OData and STAC (SpatioTemporal Asset Catalog) APIs.
*   **Constellation Status:** Sentinel-1A operated for 12 years (retired mid-2026). Sentinel-1C was launched December 5, 2024 and is fully operational; Sentinel-1D was launched November 2025. Dual-satellite global revisit cadence is maintained.
*   **Access Method:** Programmatic access uses `pystac-client` or direct HTTPS REST/OData requests. To maximize pipeline throughput and query speed, the system avoids transferring monolithic multi-gigabyte raster files, querying targeted spatial chips and analysis-ready feature metadata instead.

### 2.3 Public SAR Vessel Datasets & Remote Sensing Benchmarks
*   **SSDD (SAR Ship Detection Dataset):** 1,160 images, ~35 MB compressed. Ideal lightweight benchmark for radar detection and dimension validation.
*   **HRSID (High-Resolution SAR Images Dataset):** 5,604 high-res crop chips, ~800 MB to 1 GB. Contains vessel segmentations and scale variations.
*   **OpenSARShip:** ~11,300 chips paired with AIS records, ~1.5 GB. Useful for AIS-SAR dimension correlation.
*   **xView3-SAR:** The premier dark vessel benchmark (Defense Innovation Unit / Global Fishing Watch). Full scenes span >1 TB, but the ground truth annotations and feature metadata CSV is under 50 MB, providing thousands of labeled maritime detections (correlated vs dark).

### 2.4 Pretrained SAR Vessel Detection Models
*   Community-validated YOLOv8 and YOLOv11 architectures have documented weights on SSDD and HRSID benchmarks on GitHub and Hugging Face.
*   Instead of spending days training a raw object detector, standard base weights (e.g. YOLOv8-nano, ~6 MB) can be applied or pre-extracted morphological features can be ingested directly into the feature engineering pipeline.

### 2.5 AIS & Maritime Behavioral Analytics
*   **Decoding & Parsing:** `pyais` offers fast, dependency-free decoding of raw NMEA AIVDM/AIVDO AIS streams.
*   **Kinematic Trajectory Features:** `movingpandas` (built on GeoPandas and Shapely) computes trajectory velocity, heading changes, stop detection, and spatial curvature.
*   **Anomaly Indicators:**
    *   *AIS Gap Semantics:* Gaps >6 hours outside known coastal shadow zones indicate potential intentional disabling.
    *   *Kinematic Inconsistency:* Abrupt jumps in implied velocity (>40 knots) indicate spoofing.
    *   *Loitering & Drift:* Low SOG (<3 knots) in open ocean outside anchorage areas signifies potential Ship-to-Ship (STS) transfer or illegal fishing.

### 2.6 Vessel Identity & Registry Data
*   **ITU MARS (Maritime Mobile Access and Retrieval System):** The International Telecommunication Union provides free, public downloadable databases of registered maritime stations (MMSI, callsign, registered flag, vessel name).
*   **GFW Vessel API:** Resolves MMSI and IMO numbers to known vessel attributes.
*   **IMO GISIS & Equasis:** Official registries with restricted programmatic scraping; handled via curated candidate mappings and public ITU data.

### 2.7 Sanctions Intelligence Sources
*   **U.S. OFAC SDN List:** The official Department of the Treasury Sanctions List Service provides a compressed XML download (`sdn_xml.zip`) that is **only ~15 MB** and requires no API key. It contains complete entity details, vessel IMO numbers, callsigns, flag states, and sanction programs (e.g. IRAN, RUSSIA, DPRK).
*   **UN Security Council Consolidated List:** Official XML file available free of charge (**~2 MB**).
*   **OpenSanctions:** An excellent aggregator, but the full FollowTheMoney export is **2.42 GB**. For maximum data freshness, official authority, and sub-millisecond in-memory indexing, parsing the official OFAC and UN XML feeds directly is vastly superior.

### 2.8 Agentic AI Orchestration (LangGraph)
*   **Architecture:** LangGraph provides a cyclical, state-graph execution engine (`StateGraph`).
*   **Typed State:** State flows through nodes via a strictly typed Pydantic or TypedDict schema (`MaritimeAgentState`), avoiding untyped string passing.
*   **Conditional Routing:** Dynamic branching routes investigations based on sensor availability (e.g., if AIS data is absent, the graph routes directly to anomaly assessment with a recorded degradation note).
*   **Human-in-the-Loop:** LangGraph's `interrupt()` primitive allows an analyst to inspect flagged dark vessel cases before final bulletin generation.

### 2.9 LLM Fine-Tuning (Pillar 3)
*   **Candidate Comparison:**
    *   *LLaVA-1.6 / InternVL2:* Multi-modal vision-language models. Inefficient for textual intelligence synthesis; high VRAM (>24 GB required for fine-tuning); poor remote sensing alignment.
    *   *Llama-3.1-8B-Instruct:* High performance, but requires Hugging Face gated license approval and 16 GB base storage.
    *   *Qwen2.5-7B-Instruct (Primary Recommendation):* State-of-the-art open-weight instruction model (Apache 2.0). Outstanding structured JSON output, native support for tabular/numerical reasoning, fits in ~4.5 GB in 4-bit quantization, fine-tunable via QLoRA on a single consumer GPU (8GB-16GB VRAM) or free Colab T4/A100.
    *   *Qwen2.5-3B-Instruct (High-Throughput Edge Fallback):* Highly optimized compact model requiring only ~2 GB in 4-bit, enabling fast real-time inference and edge deployment.
*   **Fine-Tuning Paradigm:** Parameter-Efficient Fine-Tuning (PEFT) with QLoRA (Rank=16, Alpha=32) using Hugging Face `TRL` (`SFTTrainer`). The model is trained on structured evidence pairs (fused features & context → structured intelligence bulletin) to produce standardized, hallucination-free reports.
