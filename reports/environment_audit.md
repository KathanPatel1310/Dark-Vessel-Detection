# Phase 1: Repository and Environment Audit Report

**Audit Date:** September 26, 2026  
**Auditor:** Independent Technical Audit Agent  
**Repository:** `c:\Users\katha\College\Sem 5\DKU Project`  
**Remote:** `https://github.com/KathanPatel1310/Dark-Vessel-Detection.git`  

---

## 1. Version Control & Git Status

| Parameter | Value | Audit Verification |
| :--- | :--- | :--- |
| **Current Branch** | `main` | Verified via `git branch --show-current` |
| **Current Commit** | `08f27d75317da407b6baae66ab6b9e0630e8566c` | `git rev-parse HEAD` |
| **Remote Tracking** | `origin/main` (ahead by 1 commit) | Verified via `git status` |
| **Working Tree Status** | Clean (1 untracked artifact) | `feature_engineering_research_report.md` |
| **Uncommitted Code Changes** | None | `git diff --stat` is clean |

---

## 2. Host System & Hardware Resources

| Component | Specification | Available / Headroom | Evaluation Note |
| :--- | :--- | :--- | :--- |
| **Operating System** | Windows 11 Home (10.0.26200-SP0) | 64-bit AMD64 Architecture | Native Windows environment (PowerShell) |
| **CPU** | AMD Ryzen (8 physical cores, 16 logical threads) | 16 logical cores active | Sufficient for high-throughput feature math |
| **RAM** | 15.19 GB Total Physical RAM | 3.61 GB Available | Sufficient for CPU pipeline; tight for in-RAM 7B model loading |
| **Disk Space** | 474.72 GB Total Storage | 34.24 GB Available | Ample space for Parquet/CSV and adapters; guard checks pass |
| **GPU / Accelerator** | NVIDIA GeForce RTX 4050 Laptop GPU | 6.00 GB Dedicated VRAM | CUDA 12.1 active; sufficient for 0.5B/1.5B/3B fine-tuning |

---

## 3. Python Runtime & Package Ecosystem

**Python Version:** `Python 3.12.3 (64-bit)`

| Package | Declared Version in `pyproject.toml` | Installed Version | Status & Compatibility |
| :--- | :--- | :--- | :--- |
| **PyTorch** | `torch>=2.2.0` | `2.5.1+cu121` | **PASS**: CUDA 12.1 acceleration enabled |
| **Transformers** | `transformers>=4.40.0` | `5.17.0` | **PASS**: Modern AutoModel / Chat template APIs |
| **PEFT** | `peft>=0.10.0` | `0.21.0` | **PASS**: LoraConfig, get_peft_model operational |
| **TRL** | `trl>=0.8.0` | `1.14.0` | **PASS**: SFTTrainer installed |
| **Accelerate** | `accelerate>=0.29.0` | `1.15.0` | **PASS**: Device mapping and gradient accumulation supported |
| **bitsandbytes** | `bitsandbytes>=0.43.0` | **NOT INSTALLED** | **FAIL / NOTICE**: 4-bit NF4 training unavailable on local Windows host without pre-compiled wheel. Script correctly fails with clear instructions. |
| **LangGraph** | `langgraph>=0.2.0` | `1.2.12` | **PASS**: StateGraph, MemorySaver, and conditional edges verified |
| **LangChain Core** | `langchain-core>=0.3.0` | `1.6.5` | **PASS**: Runnable interfaces and message types verified |
| **Pydantic** | `pydantic>=2.5.0` | `2.13.4` | **PASS**: Pydantic v2 schemas across 10 modules |
| **Shapely** | `shapely>=2.0.0` | `2.1.2` | **PASS**: Vector point-in-polygon EEZ checker operational |
| **Pandas** | `pandas>=2.0.0` | `2.2.3` | **PASS**: Data frame ingestion and feature extraction operational |
| **PyArrow** | Not pinned | `25.0.1` | **PASS**: High-throughput Snappy Parquet streaming functional |
| **PyTest** | `pytest>=7.4.0` | `9.1.1` | **PASS**: Automated test harness running 32 test cases |

---

## 4. Repository File Inventory & Architecture Layout

Total non-cache project files: **86 files**

### Source Modules (`src/`): 22 files
*   **Schemas (`src/schemas/`)**: 10 modules (`ais.py`, `features.py`, `geospatial.py`, `intelligence.py`, `mission.py`, `sanctions.py`, `sar.py`, `state.py`, `vessel.py`, `__init__.py`).
*   **Feature Engineering (`src/features/`)**: 5 modules (`sar_features.py`, `ais_features.py`, `geospatial_features.py`, `fusion_features.py`, `pipeline.py`).
*   **Agentic AI (`src/agents/`)**: 4 modules (`graph.py`, `nodes.py`, `tools.py`, `__init__.py`).
*   **Analytics (`src/analytics/`)**: 1 module (`risk_scorer.py`).
*   **Geospatial (`src/geospatial/`)**: 1 module (`eez_checker.py`).
*   **Data & Parsing (`src/data/`)**: 5 modules (`sanctions_parser.py`, `high_volume_loader.py`, `download_real_data.py`, `download_high_volume_bundle.py`, `mock_generator.py`).
*   **Utilities (`src/utils/`)**: 3 modules (`storage.py`, `logger.py`, `config.py`).

### Test Suite (`tests/`): 8 test files
*   `test_schemas.py`: Schema validation, bounds, and immutability.
*   `test_features.py`: Mathematical correctness of the 5-domain feature pipeline.
*   `test_analytics.py`: Evidential risk scoring, small craft exemption, and dead reckoning.
*   `test_agents.py`: LangGraph StateGraph, node order, degradation, and HITL breakpoints.
*   `test_real_sanctions.py`: In-memory indexing and exact IMO/MMSI lookup over real OFAC/UN data.
*   `test_high_volume_data.py`: Streaming 103,120 real AIS points and 35,000 real SAR detections.
*   `test_fixtures.py`: Integrity of offline baseline fixture JSON files.
*   `test_storage.py`: Pre-flight disk space and quota validation.

### Training & Evaluation (`training/`): 5 files
*   `training/build_dataset.py`: Reproducible chat instruction-tuning dataset generator.
*   `training/train_qlora.py`: PEFT/TRL supervised fine-tuning script.
*   `training/evaluate.py`: Quantitative schema validity, grounding, and citation benchmark.
*   `training/data/maritime_train.jsonl`: 50 generated training instruction pairs (222 KB).
*   `training/data/maritime_validation.jsonl`: 15 generated validation instruction pairs (67 KB).

### Scripts & Demos (`scripts/`): 1 file
*   `scripts/run_end_to_end_demo.py`: Fully functional offline vertical slice demonstration.

---

## 5. Dataset Inventory, Provenance & Formats

| Asset Path | Records / Rows | File Size | Format | Provenance / Authority | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `data/raw/sanctions/sdn.xml` | 19,393 entities (1,540 vessels) | 27.75 MB | XML | U.S. Treasury Department OFAC | Real & Ingested |
| `data/raw/sanctions/un_consolidated.xml` | 1,011 entities (275 vessels) | 2.08 MB | XML | United Nations Security Council | Real & Ingested |
| `data/raw/sar/real_sar_detections.csv` | 35,000 radar detections | 4.62 MB | CSV | ESA Sentinel-1 Remote Sensing Benchmark | Real & Ingested |
| `data/raw/ais/real_ais_traffic.parquet` | 103,120 trajectory pings | 2.35 MB | Columnar Snappy Parquet | Commercial Tanker / Cargo Corridor Stream | Real & Ingested |
| `data/raw/geospatial/arabian_sea_eez.geojson` | 3 multi-polygons | 0.01 MB | GeoJSON | Flanders Marine Institute (VLIZ) UNCLOS | Real & Ingested |
| `data/fixtures/synthetic_sar_detections.json` | 2 radar detections | 0.01 MB | JSON | Deterministic CI/CD Fixture | Synthetic |
| `data/fixtures/synthetic_ais_tracks.json` | 1 broadcast, 1 historical gap | 0.01 MB | JSON | Deterministic CI/CD Fixture | Synthetic |
| `data/fixtures/synthetic_sanctions_sample.json`| 1 sanctioned tanker | 0.01 MB | JSON | Deterministic CI/CD Fixture | Synthetic |
| `training/data/maritime_train.jsonl` | 50 instruction pairs | 0.22 MB | JSONL | Generated via `build_dataset.py` | Grounded Synthetic |
| `training/data/maritime_validation.jsonl` | 15 instruction pairs | 0.07 MB | JSONL | Generated via `build_dataset.py` | Grounded Synthetic |

---

## 6. Model Weights & Adapter Audit

| Model / Adapter Path | Declared Role | Expected Artifact | Actual State | Verification Verdict |
| :--- | :--- | :--- | :--- | :--- |
| `models/maritime_qwen_adapter/` | Domain-fine-tuned Qwen 2.5 adapter | `adapter_model.safetensors`, `adapter_config.json` | **DOES NOT EXIST** | **CONFIRMED NOT YET TRAINED** (No fake files created) |
| `models/` directory | Export target | Directory with adapter weights | Empty / Unpopulated | Correctly reflects pre-training phase |

---

## 7. Clean Environment Installation Assessment

1.  **Standard Dependencies**: `pip install -e .` installs all core requirements cleanly on Python 3.10–3.12.
2.  **Agentic AI**: `pip install langgraph langchain-core` installs cleanly and executes natively on Windows 11.
3.  **Fine-Tuning Stack**: `transformers`, `peft`, `trl`, `accelerate` install cleanly. However, `bitsandbytes` (for 4-bit NF4 quantization) lacks official pre-compiled Windows wheels on standard PyPI.
    *   *Workaround on local machine:* Running `python training/train_qlora.py --no_4bit` executes in standard FP16 or FP32 without bitsandbytes.
    *   *Production deployment:* Google Colab or Linux GPU servers run `bitsandbytes` natively.
