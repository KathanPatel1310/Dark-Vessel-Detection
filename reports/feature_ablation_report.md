# Phase 5 Feature Engineering Ablation Study Report

**Execution Timestamp**: 2026-09-26T22:36:56+05:30  
**Audit Script**: `scripts/run_ablation_study.py`  
**Dataset**: Stratified sample of 10,000 radar records from `data/raw/sar/real_sar_detections.csv`  
**Prediction Target**: `is_dark_vessel` (`matched_ais == False`, base rate = $11.99\%$)  
**Model Architecture**: Random Forest Classifier ($N=100$, Depth=8, Balanced Class Weighting)  
**Data Partitioning**: 70% Train ($N=7,000$), 15% Validation ($N=1,500$), 15% Test ($N=1,500$)  

---

## 1. Ground Truth Label Provenance and Circularity Audit

> [!WARNING]
> **Data Provenance Finding: Rule-Derived Synthetic Benchmark Labels**  
> Inspection of `src/data/download_high_volume_bundle.py` reveals that while the table is named `real_sar_detections.csv` and contains realistic physical parameter distributions from the xView3 / SSDD remote sensing benchmarks, **the records and ground-truth `matched_ais` target flags are synthetically generated** using parameterized probabilistic rules:
> ```python
> is_dark = (random.random() < 0.20) if ("59.5" in str(scene["center_lon"]) or "62.0" in str(scene["center_lon"])) else (random.random() < 0.05)
> ```
> Consequently, this ablation benchmark represents a **transparent empirical evaluation on a high-fidelity synthetic benchmark**. It validates that feature groups mathematically reflect the underlying domain patterns, but must not be claimed to the professor as real sea-truth AIS transponder correlations.

---

## 2. Comparative Ablation Performance Table

| Feature Group | Features ($D$) | Accuracy | Balanced Acc | Precision | Recall | F1-Score | ROC-AUC | PR-AUC | Brier Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **A. Raw Inputs Only** | 7 | 0.9053 | 0.7423 | 0.6250 | 0.5278 | 0.5723 | 0.7914 | 0.4999 | 0.1050 |
| **B. SAR Engineered Only** | 6 | 0.9027 | 0.7480 | 0.6049 | 0.5444 | 0.5731 | 0.7715 | 0.4767 | 0.1131 |
| **C. Geospatial Engineered Only**| 5 | 0.7327 | 0.5170 | 0.1377 | 0.2333 | 0.1732 | 0.5147 | 0.1405 | 0.2136 |
| **D. All Engineered (SAR + Geo)**| 11 | 0.9053 | 0.7399 | 0.6267 | 0.5222 | 0.5697 | 0.7833 | 0.4663 | 0.1082 |
| **E. All Combined (Raw + Eng)** | **18** | **0.9073** | **0.7410** | **0.6395** | **0.5222** | **0.5749** | **0.7938** | **0.5015** | **0.1039** |
| **F. Drop SAR Morphology** | 14 | 0.9027 | 0.7384 | 0.6104 | 0.5222 | 0.5629 | 0.7893 | 0.5058 | 0.1047 |
| **G. Drop Geospatial** | 13 | 0.9040 | 0.7463 | 0.6139 | 0.5389 | 0.5740 | 0.7937 | 0.4960 | 0.1046 |

---

## 3. Confusion Matrices on Held-Out Test Set ($N=1,500$)

- **Group A (Raw Only)**:  
  `TN: 1263 | FP: 57`  
  `FN: 85   | TP: 95`
- **Group C (Geospatial Only)**:  
  `TN: 1057 | FP: 263`  
  `FN: 138  | TP: 42`
- **Group E (All Combined)**:  
  `TN: 1267 | FP: 53`  
  `FN: 86   | TP: 94`

---

## 4. Key Scientific Insights

1. **Standalone Discriminative Power**:
   - **SAR Features Dominate**: SAR physical and radiometric measurements ($L, W, \text{TCR}, \text{Area}$) provide the bulk of predictive discriminability (ROC-AUC $0.7715$).
   - **Geospatial Features Alone Fail**: Geospatial features in isolation yield near-chance performance (ROC-AUC $0.5147$, PR-AUC $0.1405$). Location alone does not dictate whether a vessel transmits AIS; rather, geospatial coordinates act as risk multipliers when combined with hull dimensions.
2. **Combination Benefit**:
   - Combining raw sensor attributes with engineered morphology (compactness, eccentricity, target area) and geospatial proximity yields the highest overall discriminative performance (ROC-AUC $0.7938$, PR-AUC $0.5015$, Brier score $0.1039$).
3. **Gini Feature Importance Hierarchy**:
   - Inspection of `reports/figures/feature_importance.png` confirms that the top predictive variables are:
     1. `raw_length_m` / `sar_length_m` (Gini weight: ~0.24)
     2. `raw_tcr_db` / `sar_tcr_db` (Gini weight: ~0.18)
     3. `sar_area_m2` (Gini weight: ~0.14)
     4. `raw_distance_shore_km` (Gini weight: ~0.11)
     5. `sar_compactness` (Gini weight: ~0.08)

---

## 5. Artifact References

- Machine-Readable Benchmark Results: [feature_ablation_results.json](file:///c:/Users/katha/College/Sem%205/DKU%20Project/reports/feature_ablation_results.json)
- ROC Curve Comparison Plot: `reports/figures/feature_ablation_roc.png`
- Feature Importance Bar Chart: `reports/figures/feature_importance.png`
