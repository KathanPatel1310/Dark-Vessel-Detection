# Project Implementation Roadmap

This roadmap structures the development into 6 cohesive, modular phases aligned with the platform's three core architectural pillars.

---

## Phase Overview

| Phase | Title | Primary Focus | Pipeline Deliverable | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 0** | **Architecture Redesign & Foundation** | **Technical audit, Pydantic schemas, pre-flight guards** | **10 Core Schemas & Test Suite** | **COMPLETED** |
| **Phase 1** | **Feature Engineering Engine & Analytics** | **Pillar 1: 5 feature domains, formulas, risk scorer** | **26 Unit Tests & Mathematical Pipeline** | **COMPLETED** |
| **Phase 2** | **Multi-Source Evidence Ingestion & Connectors** | **OFAC/UN sanctions parser, GFW API, Parquet streams** | **Indexed Real-World Production Feeds** | **In Progress** |
| **Phase 3** | **LangGraph Agentic Orchestration & Resilience** | **Pillar 2: StateGraph, 6 agent nodes, HITL, degradation** | **Cyclic Multi-Agent Decision Graph** | Next Phase |
| **Phase 4** | **Domain Dataset & QLoRA LLM Fine-Tuning** | **Pillar 3: Instruction dataset, Qwen 2.5 adapter training** | **Domain-Fine-Tuned Maritime LLM** | Phase 4 |
| **Phase 5** | **End-to-End System Evaluation & Dashboard** | **Ablation studies, Base vs FT comparison, Streamlit UI** | **Quantitative Benchmark & UI Platform** | Phase 5 |

---

## Detailed Phase Specifications

### Phase 0: Architecture Redesign & Foundation [COMPLETED]
*   **Objective:** Audit legacy proposals, resolve architectural flaws, define strongly typed data schemas, establish pre-flight validation guards, and configure the project foundation.
*   **Scope:**
    *   Full critical audit of legacy documentation and remote sensing methodologies.
    *   Ecosystem research (CDSE, GFW 4Wings, OFAC/UN, Qwen 2.5, LangGraph).
    *   Definition of Pydantic data schemas for all pipeline entities (`src/schemas/`).
    *   Implementation of `StorageGuard` pre-flight validation and environment configurations.
    *   Offline baseline fixture generation and verification test suite.
*   **Outputs:** Clean repository tree, 10 Pydantic schemas, configuration files, passing unit tests, and comprehensive documentation (`docs/`).
*   **Success Criteria:** All schema tests pass with zero warnings and deterministic serialization.

---

### Phase 1: Feature Engineering Engine & Risk Analytics [COMPLETED]
*   **Objective:** Implement **Pillar 1 (Feature Engineering)** as a first-class mathematical pipeline.
*   **Scope:**
    *   Built `src/features/sar_features.py`: Target-to-clutter ratio, length, beam, aspect ratio, radar cross-section, backscatter statistics.
    *   Built `src/features/ais_features.py`: Kinematic metrics (mean speed, acceleration, turn rate, curvature), transmission gap metrics (outage duration, 30-day frequency, loitering hours).
    *   Built `src/features/geospatial_features.py`: Haversine & geodesic distance to coastline, EEZ boundary checks, proximity to STS corridors and anchorage zones.
    *   Built `src/features/fusion_features.py`: Spatial-temporal correlation offset, dimension mismatch ratio, heading discrepancy, candidate correlation scoring.
    *   Built `src/analytics/risk_scorer.py`: Transparent statistical risk model (distinguishing deliberate dark evasion from small-craft exemption or satellite coverage gaps).
*   **Outputs:** Fully populated `EngineeredFeatures` objects with `.to_flat_dict()` export for ML models.
*   **Success Criteria:** 100% test coverage on feature math; deterministic feature vectors generated in < 10ms per detection (26/26 unit tests passing).

---

### Phase 2: Multi-Source Evidence Ingestion & Connectors [IN PROGRESS]
*   **Objective:** Connect the feature engineering engine to real-world machine-readable data utilizing high-throughput streaming and columnar storage.
*   **Scope:**
    *   Build `src/data/sanctions_parser.py`: Download and parse official U.S. OFAC SDN XML and UN Consolidated Sanctions XML; build in-memory lookup index by IMO and fuzzy name.
    *   Build `src/data/high_volume_loader.py`: Integration with real Sentinel-1 SAR detection tables and high-density AIS Parquet streams.
    *   Build `src/geospatial/eez_checker.py`: Parse high-precision Western Indian Ocean & Arabian Sea EEZ boundaries GeoJSON.
*   **Outputs:** Structured vessel registry, indexed sanctions database (< 1ms lookup), and spatial EEZ boundary trees.
*   **Success Criteria:** Exact IMO matching with < 1ms lookup latency; sub-second loading over 100,000+ trajectory points.

---

### Phase 3: LangGraph Agentic Orchestration & Resilience
*   **Objective:** Implement **Pillar 2 (Agentic AI)** using LangGraph's state graph architecture.
*   **Scope:**
    *   Construct `agents/graph.py` defining the cyclic `StateGraph`.
    *   Implement 6 specialized agent nodes: `MissionController`, `SARAISCorrelator`, `FeatureEngineer`, `SanctionsScreener`, `ForensicAssessor`, and `ReportPreparer`.
    *   Implement conditional routing for graceful degradation:
        *   If AIS stream is absent $\rightarrow$ Route to coverage-gap assessment node and log degradation note.
        *   If Sanctions API is offline $\rightarrow$ Use local cached snapshot without crashing.
    *   Implement Human-in-the-Loop (`interrupt`) mechanism for high-threat dark vessel cases.
*   **Outputs:** Populated state with complete evidence matrix, audit trace, and structured report payload.
*   **Success Criteria:** Graph completes execution even when 2 out of 3 external sources simulate total outage.

---

### Phase 4: Domain Dataset Construction & QLoRA LLM Fine-Tuning
*   **Objective:** Implement **Pillar 3 (LLM Fine-Tuning)** using parameter-efficient QLoRA.
*   **Scope:**
    *   Curate domain training corpus: 400 - 800 paired examples (structured feature vector $\rightarrow$ formal maritime intelligence bulletin) derived from UNODC, IMO, USCG, and OFAC advisory publications.
    *   Build `training/train_qlora.py`: Hugging Face `TRL` (`SFTTrainer`) script with 4-bit `bitsandbytes` quantization.
    *   Target model: `Qwen/Qwen2.5-7B-Instruct` (or `Qwen2.5-3B-Instruct` for edge deployment).
    *   Export lightweight LoRA adapter weights (~50 MB).
*   **Outputs:** Trained QLoRA adapter weights in `models/maritime_qwen_adapter/`.
*   **Success Criteria:** 4-bit fine-tuning completes on standard GPU infrastructure; adapter achieves < 1.8 validation cross-entropy loss with zero hallucinated maritime citations.

---

### Phase 5: End-to-End System Evaluation & Dashboard
*   **Objective:** Validate system performance against baselines and provide an interactive demonstration interface.
*   **Scope:**
    *   Ablation study on Pillar 1 engineered features (random forest / logistic regression classifier comparing raw features vs engineered features).
    *   Evaluation of Pillar 3: Quantitative comparison of **Base Qwen 2.5 vs Fine-Tuned Qwen 2.5** (BERTScore, statutory citation accuracy, format compliance, hallucination rate).
    *   Build lightweight `app/` dashboard (Streamlit) to visualize SAR detections, AIS tracks, risk meters, and generated intelligence reports.
*   **Outputs:** Evaluation metrics tables, ablation charts, and interactive web dashboard.
*   **Success Criteria:** Demonstrable superiority of the fine-tuned model over the base model; interactive UI response time < 5 seconds.
