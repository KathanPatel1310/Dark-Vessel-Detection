# Phase 10 Fine-Tuning Dataset Audit Report

**Execution Timestamp**: 2026-09-26T22:41:42+05:30  
**Audit Script**: `scripts/audit_fine_tuning_dataset.py`  
**Dataset Directory**: `training/data/` (`maritime_train.jsonl`, `maritime_validation.jsonl`)  
**Base Tokenizer**: `Qwen/Qwen2.5-0.5B-Instruct`  

---

## 1. Quantitative Dataset Statistics

| Metric | Training Split (`maritime_train.jsonl`) | Validation Split (`maritime_validation.jsonl`) |
| :--- | :---: | :---: |
| **Total Sample Count** | 50 examples | 15 examples |
| **Mean Prompt Length (Tokens)** | 231.2 tokens | 228.4 tokens |
| **Max Prompt Length (Tokens)** | 239 tokens | 236 tokens |
| **Mean Completion Length (Tokens)**| 941.4 tokens | 938.2 tokens |
| **Max Completion Length (Tokens)** | 1003 tokens | 988 tokens |
| **Class: LOW Threat** | 17 (34.0%) | 5 (33.3%) |
| **Class: MEDIUM Threat** | 17 (34.0%) | 3 (20.0%) |
| **Class: HIGH Threat** | 8 (16.0%) | 4 (26.7%) |
| **Class: SEVERE Threat** | 8 (16.0%) | 3 (20.0%) |

---

## 2. Integrity, Overlap, and Data Leakage Analysis

1. **Exact Duplicate Check**:
   - Zero exact duplicate prompt-completion pairs between train and validation splits ($0$ overlaps).
   - Validation cases use unique target identifiers, coordinates, and distinct vessel attributes.
2. **Near-Duplicate Analysis**:
   - 45 prompt pairs in the training set exhibit lexical similarity $> 0.95$.
   - **Reason**: The prompts are structured JSON payloads adhering to a rigid schema:
     `{"mission_id": "...", "sar_detection": {...}, "ais_kinematics": {...}, "geospatial": {...}}`.
     The schema keys are identical; only the numerical measurements and vessel identifiers vary.
3. **Evaluation Circularity & Template Memorization**:
   > [!WARNING]
   > **Circularity Finding: Rule-Derived Completions Checked Against Identical Rules**  
   > The target completions in both `maritime_train.jsonl` and `maritime_validation.jsonl` are synthesized by `training/build_dataset.py` using deterministic functions (`FeaturePipeline.extract()` and `MaritimeRiskScorer.compute_risk_assessment()`).
   > When `training/evaluate.py` evaluates a model against the validation set, it checks whether the model's generated JSON matches the exact structure and statutory strings produced by these rules.
   > Thus, fine-tuning on this dataset teaches the LLM to **memorize a structured template formatter**, rather than teaching novel inductive reasoning.

---

## 3. Statutory and Evidential Grounding

1. **SOLAS Citations**:
   - Accurately cites *SOLAS Chapter V, Regulation 19* for commercial hulls $\ge 100$m operating without AIS.
2. **UNCLOS Citations**:
   - Accurately cites *UNCLOS Article 56/73* when dark vessels enter Indian Ocean sovereign EEZ corridors.
3. **OFAC/UN Sanctions Citations**:
   - Accurately quotes Executive Order 14024 and UN Security Council Resolution 2270 when matched against genuine OFAC SDN records.
4. **Degraded Evidence Representation**:
   - Cases with missing AIS properly emit `AIS Transmission Status: NON_TRANSMITTING` and flag evidence degradation rather than fabricating fake coordinates.
