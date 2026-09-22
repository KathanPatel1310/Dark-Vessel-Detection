# Maritime Intelligence & Dark Vessel Detection System

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-22%20passed-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An academic research prototype for maritime domain awareness, fusing Synthetic Aperture Radar (SAR) imagery, Automatic Identification System (AIS) vessel tracking, and live sanctions intelligence. 

The system investigates suspicious maritime anomalies, engineers domain-specific features, reasons across evidence through a resilient multi-agent graph (LangGraph), and utilizes a domain-fine-tuned open-weight LLM to generate structured intelligence bulletins.

---

## The Three Core Pillars

This project is built around the three primary academic evaluation requirements:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. FEATURE ENGINEERING ENGINE (COMPLETED)                                   │
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
| **Real Sanctions Data (OFAC + UN)** | 1,563 official real sanctioned vessels, IMOs, programs | **~29.8 MB** | **Downloaded & Verified** |
| **Real Maritime EEZ Boundaries** | Legal Indian Ocean & Arabian Sea EEZ boundaries | **< 1 MB** | **Generated & Verified** |
| **Pillar 1 Feature Engineering Code** | 5 feature extractors + risk scorer + 22 unit tests | **~0.2 MB** | **Implemented & Tested** |
| **Synthetic Baseline Fixtures** | Offline fallback test cases | **< 100 KB** | **Ready & Built** |
| **Tier 1: LLM Fallback (4-bit)** | Qwen2.5-3B-Instruct QLoRA fine-tuning | **~2.0 GB** | User approval requested in Phase 4 |
| **Tier 2: Standard LLM (4-bit)** | Qwen2.5-7B-Instruct QLoRA fine-tuning | **~4.5 GB** | User approval requested in Phase 4 |

---

## Development Status

- [x] **Phase 0: Project Discovery, Redesign & Foundation** (Completed)
- [x] **Phase 1: Feature Engineering Engine & Risk Analytics** (Completed - 22/22 unit tests passing)
- [ ] **Phase 2: Multi-Source Evidence Ingestion & Live Connectors** (Next phase)
- [ ] **Phase 3: LangGraph Agentic Orchestration & Resilience**
- [ ] **Phase 4: Domain Dataset Construction & QLoRA LLM Fine-Tuning**
- [ ] **Phase 5: End-to-End System Evaluation & Interactive Dashboard**
