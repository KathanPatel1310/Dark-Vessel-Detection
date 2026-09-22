# Maritime Intelligence & Dark Vessel Detection System

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-10%20passed-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An academic research prototype for maritime domain awareness, fusing Synthetic Aperture Radar (SAR) imagery, Automatic Identification System (AIS) vessel tracking, and live sanctions intelligence. 

The system investigates suspicious maritime anomalies, engineers domain-specific features, reasons across evidence through a resilient multi-agent graph (LangGraph), and utilizes a domain-fine-tuned open-weight LLM to generate structured intelligence bulletins.

---

## The Three Core Pillars

This project is built around the three primary academic evaluation requirements:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. FEATURE ENGINEERING ENGINE                                               │
│    Explicit mathematical extraction across 5 domains: SAR backscatter/      │
│    geometry, AIS kinematics/outages, geospatial sovereignty, historical     │
│    indicators, and SAR-AIS spatial-temporal fusion metrics.                 │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. AGENTIC AI (LangGraph)                                                   │
│    Multi-agent workflow with shared typed Pydantic state, specialized tool  │
│    calling, conditional routing, graceful degradation, and human-in-the-    │
│    loop oversight.                                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. LLM FINE-TUNING (QLoRA)                                                  │
│    Parameter-efficient supervised fine-tuning of Qwen 2.5 (7B / 3B) on      │
│    maritime crime & legal intelligence datasets (UNODC/SOLAS/UNCLOS/OFAC),  │
│    quantitatively evaluated against the base foundation model.              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Strict Storage Safety Policy

To prevent unintended storage consumption on local development machines, **all external downloads are gated and audited in advance**.

| Component / Tier | Description | Storage Footprint | Status |
| :--- | :--- | :--- | :--- |
| **Tier 1: Minimal Baseline** | Synthetic fixtures, unit tests, mock feeds | **< 1 MB** | **Ready & Built** |
| **Tier 1: Official Sanctions** | US OFAC SDN XML + UN Consolidated XML | **~17 MB** | Configured for Phase 2 |
| **Tier 1: High-Res EEZ** | Indian Ocean & Arabian Sea EEZ boundaries | **< 2 MB** | Configured for Phase 2 |
| **Tier 1: LLM Fallback (4-bit)** | Qwen2.5-3B-Instruct QLoRA fine-tuning | **~2.0 GB** | User approval requested in Phase 4 |
| **Tier 2: Standard LLM (4-bit)** | Qwen2.5-7B-Instruct QLoRA fine-tuning | **~4.5 GB** | User approval requested in Phase 4 |

---

## Repository Structure

```
.
├── configs/
│   └── config.yaml             # Pipeline thresholds, geographic ROI, and model configs
├── docs/
│   ├── research.md             # Critical audit of legacy PDF & domain research
│   ├── architecture.md         # Detailed 3-pillar architecture and data flow
│   ├── data_sources.md         # Data sources, API endpoints & storage footprints
│   ├── decisions.md            # Architectural Decision Records (ADRs)
│   └── roadmap.md              # 6-phase development roadmap
├── data/
│   ├── fixtures/               # Small synthetic test data (< 100 KB total)
│   ├── raw/                    # Cached external downloads (.gitkeep)
│   ├── interim/                # Intermediate preprocessed data (.gitkeep)
│   └── processed/              # Fused feature vectors (.gitkeep)
├── src/
│   ├── schemas/                # Typed Pydantic models (Pillars 1, 2, and 3)
│   │   ├── mission.py          # Mission & bounding box definitions
│   │   ├── sar.py              # SARDetection and SARScene
│   │   ├── ais.py              # AISObservation and AISGap
│   │   ├── vessel.py           # VesselCandidate and VesselIdentity
│   │   ├── geospatial.py       # GeoContext and zone risk tags
│   │   ├── sanctions.py        # SanctionMatch and SanctionsResult
│   │   ├── features.py         # EngineeredFeatures (Pillar 1)
│   │   ├── intelligence.py     # RiskAssessment & IntelligenceReport (Pillar 3)
│   │   └── state.py            # MaritimeAgentState for LangGraph (Pillar 2)
│   ├── data/                   # Data connectors and mock generators
│   │   └── mock_generator.py   # Explicit synthetic fixture generator
│   ├── features/               # (Planned Phase 1: Feature calculators)
│   ├── analytics/              # (Planned Phase 1: Risk & anomaly scorers)
│   ├── models/                 # (Planned Phase 4: Model loading & inference)
│   └── utils/                  # StorageGuard, logger, config loaders
├── agents/                     # (Planned Phase 3: LangGraph agent nodes)
├── training/                   # (Planned Phase 4: QLoRA SFT training scripts)
├── evaluation/                 # (Planned Phase 5: Ablation & Base vs FT metrics)
├── tests/                      # Unit test suite (unittest / pytest compatible)
│   ├── test_schemas.py         # Schema validation & feature flattening tests
│   ├── test_fixtures.py        # Fixture loading and parsing tests
│   └── test_storage.py         # StorageGuard verification tests
├── .env.example                # Sample environment variables
├── pyproject.toml              # Clean dependencies specification
└── README.md
```

---

## Quickstart & Verification

### 1. Run Unit Tests (Built-in `unittest`)
Zero external dependencies required beyond Pydantic:
```bash
python -m unittest discover -s tests
```
*Expected: 10 passing tests in < 0.05 seconds.*

### 2. Generate Synthetic Offline Fixtures
To regenerate or inspect synthetic test cases:
```bash
python src/data/mock_generator.py
```

### 3. Check Local Disk Space
The built-in `StorageGuard` ensures downloads only proceed with adequate safety margins:
```python
from src.utils.storage import StorageGuard
free_gb = StorageGuard.get_disk_free_gb(".")
print(f"Available free disk space: {free_gb:.2f} GB")
```

---

## Development Status

- [x] **Phase 0: Project Discovery, Redesign & Foundation** (Completed)
- [ ] **Phase 1: Feature Engineering Engine & Risk Analytics** (Ready to begin)
- [ ] **Phase 2: Multi-Source Evidence Ingestion & Connectors**
- [ ] **Phase 3: LangGraph Agentic Orchestration & Resilience**
- [ ] **Phase 4: Domain Dataset Construction & QLoRA LLM Fine-Tuning**
- [ ] **Phase 5: End-to-End System Evaluation & Interactive Dashboard**
