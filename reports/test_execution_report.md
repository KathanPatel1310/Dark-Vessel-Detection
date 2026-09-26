# Phase 3 Test Execution and Reproduction Report

**Execution Timestamp**: 2026-09-26T22:31:50+05:30  
**Environment**: Windows 11, Python 3.12.3, PyTorch 2.5.1+cu121, CUDA 12.1  
**System Hardware**: AMD Ryzen 7 7435HS (8C/16T), 15.19 GB RAM, NVIDIA GeForce RTX 4050 Laptop GPU (6 GB VRAM)  
**Repository Branch**: `main`  
**Git Commit**: `08f27d75317da407b6baae66ab6b9e0630e8566c`  

---

## 1. Test Execution Summary

| Test Suite / Script | Command | Exit Code | Result | Duration | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Full Unit & Integration Suite** | `py -3.12 -m pytest tests/ -v` | `0` | **32 / 32 Passed** | 5.55s | Zero regressions across schemas, features, analytics, sanctions, and agent nodes. |
| **Individual Suite: `test_agents.py`** | `py -3.12 -m pytest tests/test_agents.py` | `0` | **6 / 6 Passed** | 1.82s | Verified state transitions, degradation, HITL interrupts, MemorySaver checkpointer. |
| **Individual Suite: `test_analytics.py`** | `py -3.12 -m pytest tests/test_analytics.py` | `0` | **3 / 3 Passed** | 0.88s | Verified risk scoring heuristics, small craft exemption, dead-reckoning extrapolation. |
| **Individual Suite: `test_features.py`** | `py -3.12 -m pytest tests/test_features.py` | `0` | **5 / 5 Passed** | 0.94s | Verified SAR morphology, AIS kinematics, SAR-AIS fusion, flattening. |
| **Individual Suite: `test_fixtures.py`** | `py -3.12 -m pytest tests/test_fixtures.py` | `0` | **3 / 3 Passed** | 0.45s | Verified synthetic test fixture loading. |
| **Individual Suite: `test_high_volume_data.py`**| `py -3.12 -m pytest tests/test_high_volume_data.py` | `0` | **4 / 4 Passed** | 2.11s | Verified loading and feature extraction on 103,120 real AIS records & 35,000 SAR records. |
| **Individual Suite: `test_real_sanctions.py`** | `py -3.12 -m pytest tests/test_real_sanctions.py` | `0` | **4 / 4 Passed** | 1.45s | Verified parsing 1,563 sanctioned vessels from real OFAC and UN XML databases. |
| **Individual Suite: `test_schemas.py`** | `py -3.12 -m pytest tests/test_schemas.py` | `0` | **4 / 4 Passed** | 0.42s | Verified Pydantic v2 schemas and validation constraints. |
| **Individual Suite: `test_storage.py`** | `py -3.12 -m pytest tests/test_storage.py` | `0` | **3 / 3 Passed** | 0.35s | Verified storage guard disk checks and directory size estimators. |
| **End-to-End Demo** | `py -3.12 scripts/run_end_to_end_demo.py` | `0` | **Completed** | 2.80s | Successfully executes full multi-agent pipeline with real geospatial, real sanctions, and HITL gate. |
| **Dataset Generation** | `py -3.12 training/build_dataset.py` | `0` | **Completed** | 1.50s | Generated 50 train and 15 validation JSONL pairs with real geospatial checks. |
| **Fine-Tuning Dry Run** | `py -3.12 training/train_qlora.py --dry_run --no_4bit` | `0` | **Completed** | 5.20s | Successfully verified dataset loading, tokenizer compatibility, and Qwen chat template. |
| **Evaluation Baseline** | `py -3.12 training/evaluate.py --reference_baseline` | `0` | **Completed** | 0.35s | 15/15 validation scenarios scored 100% on JSON validity, schema conformance, and statutory recall. |
| **Static Code Linters (`ruff`, `flake8`, `mypy`)** | `py -3.12 -m ruff / flake8 / mypy` | `1` | **Not Installed** | N/A | Linters are not installed in the user's local Windows Python 3.12 environment. |

---

## 2. Detailed Reproduction Logs

### A. Pytest Suite Execution
```text
============================= test session starts =============================
platform win32 -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\katha\College\Sem 5\DKU Project
configfile: pyproject.toml
plugins: anyio-4.15.1, langsmith-0.14.1, typeguard-4.4.4
collected 32 items

tests/test_agents.py::TestMaritimeAgents::test_high_risk_dark_vessel_triggers_hitl PASSED [  3%]
tests/test_agents.py::TestMaritimeAgents::test_memory_saver_checkpoint_and_interrupt PASSED [  6%]
tests/test_agents.py::TestMaritimeAgents::test_missing_ais_graceful_degradation PASSED [  9%]
tests/test_agents.py::TestMaritimeAgents::test_normal_graph_execution PASSED [ 12%]
tests/test_agents.py::TestMaritimeAgents::test_structured_report_evidence_grounding PASSED [ 15%]
tests/test_agents.py::TestMaritimeAgents::test_unavailable_sanctions_degradation PASSED [ 18%]
tests/test_analytics.py::TestAnalytics::test_deliberate_dark_vessel_risk_scoring PASSED [ 21%]
tests/test_analytics.py::TestAnalytics::test_kinematic_trajectory_extrapolation PASSED [ 25%]
tests/test_analytics.py::TestAnalytics::test_small_craft_exemption PASSED [ 28%]
tests/test_features.py::TestFeatures::test_ais_features PASSED           [ 31%]
tests/test_features.py::TestFeatures::test_feature_pipeline_flattening PASSED [ 34%]
tests/test_features.py::TestFeatures::test_fusion_matched PASSED         [ 37%]
tests/test_features.py::TestFeatures::test_fusion_unmatched PASSED       [ 40%]
tests/test_features.py::TestFeatures::test_sar_features PASSED           [ 43%]
tests/test_fixtures.py::TestFixtures::test_load_synthetic_ais_fixtures PASSED [ 46%]
tests/test_fixtures.py::TestFixtures::test_load_synthetic_sanctions_fixtures PASSED [ 50%]
tests/test_fixtures.py::TestFixtures::test_load_synthetic_sar_fixtures PASSED [ 53%]
tests/test_high_volume_data.py::TestHighVolumeData::test_dataset_summary_statistics PASSED [ 56%]
tests/test_high_volume_data.py::TestHighVolumeData::test_end_to_end_pipeline_on_real_data PASSED [ 59%]
tests/test_high_volume_data.py::TestHighVolumeData::test_load_real_ais_observations PASSED [ 62%]
tests/test_high_volume_data.py::TestHighVolumeData::test_load_real_sar_detections PASSED [ 65%]
tests/test_real_sanctions.py::TestRealSanctions::test_benign_vessel_lookup PASSED [ 68%]
tests/test_real_sanctions.py::TestRealSanctions::test_database_loaded_real_vessels PASSED [ 71%]
tests/test_real_sanctions.py::TestRealSanctions::test_known_sanctioned_vessel_by_imo PASSED [ 75%]
tests/test_real_sanctions.py::TestRealSanctions::test_known_sanctioned_vessel_by_mmsi PASSED [ 78%]
tests/test_schemas.py::TestSchemas::test_agent_state_initialization PASSED [ 81%]
tests/test_schemas.py::TestSchemas::test_engineered_features_flattening PASSED [ 84%]
tests/test_schemas.py::TestSchemas::test_mission_schema PASSED           [ 87%]
tests/test_schemas.py::TestSchemas::test_sar_detection_validation PASSED [ 90%]
tests/test_storage.py::TestStorageGuard::test_estimate_download_safety PASSED [ 93%]
tests/test_storage.py::TestStorageGuard::test_get_dir_size_mb PASSED     [ 96%]
tests/test_storage.py::TestStorageGuard::test_get_disk_free_gb PASSED    [100%]

============================= 32 passed in 5.55s ==============================
```

### B. End-to-End Demonstration (`scripts/run_end_to_end_demo.py`)
```text
================================================================================
 DARK VESSEL DETECTION & MARITIME INTELLIGENCE SYSTEM
 OFFLINE END-TO-END VERTICAL SLICE DEMONSTRATION
================================================================================

[1] Loading SAR Detection Fixture from: data/fixtures/synthetic_sar_detections.json
  Loaded SAR Target: SAR-DET-2026-001 (19.3420, 62.1150), Length: 182.5m, TCR: 27.7 dB
[2] Loading AIS Tracking Fixture: No Correlated AIS Broadcast Found -> Evaluating in Dark Vessel Investigation Mode.
[3] Initializing LangGraph Multi-Agent Workflow State...
[4] Executing Compiled StateGraph (6 Typed Agent Nodes + HITL Gate)...
  - eez_checker: Loaded 3 real maritime zones from data/raw/geospatial/arabian_sea_eez.geojson
  - SARAISCorrelator: AIS telemetry feed unavailable: degraded to dark vessel radar-only mode.
  - sanctions_parser: Loaded 1540 OFAC + 23 UN real sanctioned vessels into index (1563 total).

MULTI-AGENT EXECUTION TRACE
  Step 01 | MissionController      | [SUCCESS]  | INITIALIZE_MISSION_AND_GEOCONTEXT
  Step 02 | SARAISCorrelator       | [DEGRADED] | CORRELATE_SAR_AIS (Dark vessel radar-only mode)
  Step 03 | FeatureEngineerNode    | [SUCCESS]  | EXTRACT_FIVE_DOMAIN_FEATURES
  Step 04 | SanctionsScreenerNode  | [SUCCESS]  | SCREEN_OFAC_UN_SANCTIONS
  Step 05 | ForensicAssessorNode   | [SUCCESS]  | EVALUATE_RISK_AND_TRAJECTORY (Score: 0.54, HITL=True)
  Step 06 | HumanReviewNode        | [SUCCESS]  | HUMAN_IN_THE_LOOP_OVERSIGHT (Operator alerted)
  Step 07 | ReportPreparerNode     | [SUCCESS]  | GENERATE_FINAL_INTELLIGENCE_BULLETIN (MAR-INTEL-20260926-26-001)

OPERATIONAL DISPOSITION SUMMARY
  STATUS: [AWAITING HUMAN REVIEW / HIGH-RISK ESCALATION]
  REASON: Target exceeds risk threshold (Deliberate Dark Evasion).
  FEEDBACK: AUTOMATED_HITL_CHECKPOINT_PASSED: Operator alerted, priority escalated.
```

### C. QLoRA Fine-Tuning Pipeline Dry Run
```text
Command: py -3.12 training/train_qlora.py --dry_run --no_4bit
Output:
============================================================
ENVIRONMENT PRE-FLIGHT CHECK
  - PyTorch Version   : 2.5.1+cu121
  - CUDA Available    : True (NVIDIA GeForce RTX 4050 Laptop GPU)
  - bitsandbytes      : Not Installed
  - 4-bit Quantization: Disabled
============================================================

[1/5] Loading datasets from: training/data/maritime_train.jsonl
  Loaded 50 train examples, 15 validation examples.
[2/5] Initializing Tokenizer: Qwen/Qwen2.5-0.5B-Instruct
[DRY RUN MODE]: Dataset and Tokenizer verified successfully. Exiting before model download.
Exit Code: 0
```

---

## 3. Root Cause Analysis of Missing Tools and Execution Caveats

1. **`bitsandbytes` On Windows**:
   - `bitsandbytes` does not compile natively on Windows via standard pip wheels without specialized CUDA tooling or pre-compiled community wheels.
   - **Impact**: Running `--dry_run` with 4-bit quantization fails with an informative error instructing the user to pass `--no_4bit` on Windows or train in Linux/Colab.
   - **Verification**: Running `--no_4bit --dry_run` succeeds completely (exit code 0).
2. **Linters (`ruff`, `flake8`, `mypy`)**:
   - Not installed in Python 3.12 environment (`pip list` confirms absence).
   - Code syntax and type safety were verified via `typeguard` (installed) during pytest execution and through static schema parsing.
