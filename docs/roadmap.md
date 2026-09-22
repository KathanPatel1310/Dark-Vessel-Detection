# Project Implementation Roadmap

This roadmap structures the development into 6 cohesive, modular phases aligned with the professor's three evaluation pillars.

---

## Phase Overview

| Phase | Title | Primary Focus | Expected Storage Impact | Estimated Effort |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 0** | **Project Discovery, Redesign & Foundation** | **Technical audit, schemas, storage guard, test suite** | **< 1 MB** | **COMPLETED** |
| **Phase 1** | **Feature Engineering Engine & Risk Analytics** | **Pillar 1: 5 feature domains, formulas, ablation base** | **< 5 MB** | Next Phase |
| **Phase 2** | **Multi-Source Evidence Ingestion & Connectors** | **OFAC/UN sanctions parser, GFW API, mock feeds** | **~20 MB** | Phase 2 |
| **Phase 3** | **LangGraph Agentic Orchestration & Resilience** | **Pillar 2: StateGraph, 6 agent nodes, HITL, degradation** | **< 10 MB** | Phase 3 |
| **Phase 4** | **Domain Dataset & QLoRA LLM Fine-Tuning** | **Pillar 3: Instruction dataset, Qwen 2.5 adapter training** | **~2 GB (3B) or ~4.5 GB (7B)** | Phase 4 |
| **Phase 5** | **End-to-End System Evaluation & Dashboard** | **Ablation studies, Base vs FT comparison, Streamlit UI** | **< 50 MB** | Phase 5 |

---

## Detailed Phase Specifications

### Phase 0: Project Discovery, Redesign & Foundation [COMPLETED]
*   **Objective:** Audit the legacy proposal, resolve architectural flaws, define typed data schemas, establish strict storage guards, and configure the project foundation.
*   **Scope:**
    *   Full critical audit of the original PDF documentation.
    *   Ecosystem research (CDSE, GFW 4Wings, OFAC/UN, Qwen 2.5, LangGraph).
    *   Definition of Pydantic data schemas for all pipeline entities (`src/schemas/`).
    *   Implementation of `StorageGuard` and environment configurations.
    *   Offline synthetic fixture generation and verification test suite.
*   **Inputs:** Original project PDF.
*   **Outputs:** Clean repository tree, 10 Pydantic schemas, configuration files, 10 passing unit tests, and comprehensive documentation (`docs/`).
*   **Success Criteria:** All schema tests pass with zero warnings; disk usage remains < 1 MB.

---

### Phase 1: Feature Engineering Engine & Risk Analytics [NEXT RECOMMENDED PHASE]
*   **Objective:** Implement **Pillar 1 (Feature Engineering)** as a first-class mathematical pipeline.
*   **Scope:**
    *   Build `src/features/sar_features.py`: Target-to-clutter ratio, length, beam, aspect ratio, radar cross-section, backscatter statistics.
    *   Build `src/features/ais_features.py`: Kinematic metrics (mean speed, acceleration, turn rate, curvature), transmission gap metrics (outage duration, 30-day frequency, loitering hours).
    *   Build `src/features/geospatial_features.py`: Haversine & geodesic distance to coastline, EEZ boundary checks, proximity to STS corridors and anchorage zones.
    *   Build `src/features/fusion_features.py`: Spatial-temporal correlation offset, dimension mismatch ratio, heading discrepancy, candidate correlation scoring.
    *   Build `src/analytics/risk_scorer.py`: Transparent statistical risk model (distinguishing deliberate dark evasion from small-craft exemption or satellite coverage gaps).
*   **Inputs:** SARDetection and AISObservation objects.
*   **Outputs:** Fully populated `EngineeredFeatures` objects with `.to_flat_dict()` export for ML models.
*   **Tests:** Unit tests verifying mathematical correctness of all formulas against edge cases.
*   **Success Criteria:** 100% test coverage on feature math; deterministic feature vectors generated in < 10ms per detection.
*   **Storage Impact:** < 5 MB (pure Python code).

---

### Phase 2: Multi-Source Evidence Ingestion & Connectors
*   **Objective:** Connect the feature engineering engine to real-world machine-readable data while maintaining strict storage preservation.
*   **Scope:**
    *   Build `src/data/sanctions_loader.py`: Download and parse official U.S. OFAC SDN XML (~15 MB) and UN Consolidated Sanctions XML (~2 MB); build in-memory lookup index by IMO and fuzzy name.
    *   Build `src/data/gfw_connector.py`: Integration with Global Fishing Watch API for on-demand SAR-AIS queries without bulk downloading.
    *   Build `src/geospatial/zones.py`: Parse lightweight Western Indian Ocean & Arabian Sea EEZ boundaries GeoJSON (< 2 MB).
*   **Inputs:** Official sanctions XML files, GFW API credentials (optional, fallback to fixtures).
*   **Outputs:** Structured vessel registry, indexed sanctions database, and spatial EEZ boundary trees.
*   **Tests:** Verification of sanctions screening accuracy against known historical test cases (e.g. Iranian oil tankers).
*   **Success Criteria:** Exact IMO matching with < 1ms lookup latency; total downloaded data < 20 MB.
*   **Storage Impact:** ~17 MB total.

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
*   **Inputs:** `MaritimeAgentState` initialized with target coordinates and time window.
*   **Outputs:** Populated state with complete evidence matrix, audit trace, and structured report payload.
*   **Tests:** Graph traversal tests verifying degradation branches and state immutability.
*   **Success Criteria:** Graph completes execution even when 2 out of 3 external sources simulate total outage.
*   **Storage Impact:** < 10 MB.

---

### Phase 4: Domain Dataset Construction & QLoRA LLM Fine-Tuning
*   **Objective:** Implement **Pillar 3 (LLM Fine-Tuning)** using parameter-efficient QLoRA.
*   **Scope:**
    *   Curate domain training corpus: 400 - 800 paired examples (structured feature vector $\rightarrow$ formal maritime intelligence bulletin) derived from UNODC, IMO, USCG, and OFAC advisory publications.
    *   Build `training/train_qlora.py`: Hugging Face `TRL` (`SFTTrainer`) script with 4-bit `bitsandbytes` quantization.
    *   Target model: `Qwen/Qwen2.5-7B-Instruct` (or `Qwen2.5-3B-Instruct` for 2GB ultra-low storage).
    *   Export lightweight LoRA adapter weights (~50 MB).
*   **Inputs:** Instruction dataset JSONL (~3.5 MB).
*   **Outputs:** Trained QLoRA adapter weights in `models/maritime_qwen_adapter/`.
*   **Tests:** Loss curve convergence; inference test on held-out test splits.
*   **Success Criteria:** 4-bit fine-tuning completes within budget on Colab T4/A100 or student GPU; adapter achieves < 1.8 validation cross-entropy loss.
*   **Storage Impact:** ~2.0 GB (3B model) or ~4.5 GB (7B model). *(User approval requested prior to download)*.

---

### Phase 5: End-to-End System Evaluation & Dashboard
*   **Objective:** Validate system performance against baselines and provide an interactive demonstration interface.
*   **Scope:**
    *   Ablation study on Pillar 1 engineered features (random forest / logistic regression classifier comparing raw features vs engineered features).
    *   Evaluation of Pillar 3: Quantitative comparison of **Base Qwen 2.5 vs Fine-Tuned Qwen 2.5** (BERTScore, statutory citation accuracy, format compliance, hallucination rate).
    *   Build lightweight `app/` dashboard (Streamlit) to visualize SAR detections, AIS tracks, risk meters, and generated intelligence reports.
*   **Inputs:** Real & synthetic test scenes from the Arabian Sea / Indian Ocean.
*   **Outputs:** Evaluation metrics tables, ablation charts, and interactive web dashboard.
*   **Tests:** End-to-end integration test from query coordinate to final rendered report.
*   **Success Criteria:** Demonstrable superiority of the fine-tuned model over the base model; interactive UI response time < 5 seconds.
*   **Storage Impact:** < 50 MB.
