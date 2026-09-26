# Phase 6 Analytical Risk Scorer Validation and Sensitivity Report

**Execution Timestamp**: 2026-09-26T22:38:19+05:30  
**Audit Script**: `scripts/validate_risk_and_trajectory.py`  
**Target Code**: `src/analytics/risk_scorer.py` (`MaritimeRiskScorer.evaluate_dark_vessel_probability`, `MaritimeRiskScorer.compute_risk_assessment`)  
**Figure Generated**: `reports/figures/risk_sensitivity.png`  

---

## 1. Statistical and Scientific Assessment of "Probability"

> [!CAUTION]
> **Scientific Finding: Heuristic Additive Score, Not Statistical Probability**  
> The function `evaluate_dark_vessel_probability()` computes a value between $0.05$ and $0.98$ using discrete additive offsets starting from a neutral base of $0.50$:
> - Length $< 30.0$m: $-0.35$
> - Length $\ge 100.0$m: $+0.30$
> - Coast distance $> 100.0$km: $+0.15$
> - STS zone distance $< 80.0$km: $+0.15$
> - AIS outage duration $\ge 12.0$h: $+0.10$
> 
> **Evaluation**: This score is **not calibrated** against empirical likelihoods via logistic regression, Platt scaling, or Bayesian belief networks. Calling this value "probability" is **scientifically unjustified**. It is a **heuristic evidential suspicion score**.

---

## 2. Threshold Sensitivity Analysis & Step Discontinuities

Inspection of the sensitivity curves in `reports/figures/risk_sensitivity.png` reveals several hard-coded step boundaries:

1. **Vessel Length Discontinuity ($30.0$m and $100.0$m)**:
   - Below $30.0$m: The score drops by $0.35$ (small craft exemption under SOLAS Chapter V/19).
   - Above $100.0$m: The score increases by $0.30$.
   - **Limitation**: Between $30.0$m and $99.9$m (which includes 50m–90m coastal freighters and tugs legally mandated under SOLAS at $\ge 300$ GT), no size adjustment is applied.
2. **Deepwater Offshore Discontinuity ($100.0$km)**:
   - At $99.9$km from coast, score is $0.50$; at $100.1$km, score steps up immediately by $+0.15$ to $0.65$.
3. **STS Rendezvous Corridor Proximity ($80.0$km)**:
   - Within $80$km of an STS zone (e.g. Fujairah or Arabian Sea Deepwater Sector), suspicion increases by $+0.15$.
4. **AIS Transmission Silence Duration ($12.0$h)**:
   - An outage of $11.9$ hours receives $0$ penalty; an outage of $12.0$ hours receives $+0.10$.

---

## 3. Monotonicity and Calibration Verification

| Variable | Theoretical Expectation | Code Monotonicity | Verification Status | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Vessel Length** | Monotonically increasing suspicion | Monotonic piecewise step | **VERIFIED** | Piecewise constant with discrete steps at 30m, 100m. |
| **Coastline Distance** | Increasing suspicion further offshore | Monotonic step | **VERIFIED** | Binary step at 100 km. |
| **STS Proximity** | Increasing suspicion closer to STS | Monotonic step | **VERIFIED** | Inverted distance step at 80 km. |
| **Outage Duration** | Increasing suspicion with longer gap | Monotonic step | **VERIFIED** | Binary step at 12 hours. |
| **Spatially Correlated AIS**| Near-zero suspicion if AIS matches | Immediate override ($0.05$) | **VERIFIED** | Immediately classifies as `CORRELATED_BENIGN`. |

---

## 4. Legal Assumptions and Statutory Accuracy

1. **SOLAS Chapter V, Regulation 19**:
   - **Code Assumption**: Exempts vessels $<30$m and mandates vessels $\ge 100$m.
   - **Maritime Law Audit**: Accurate in intent, but SOLAS formally mandates AIS for all ships $\ge 300$ gross tonnage (GT) on international voyages, all cargo ships $\ge 500$ GT not on international voyages, and all passenger ships regardless of size. Length is a proxy; 300 GT typically corresponds to $40\text{--}45$m length depending on vessel hull design.
2. **UNCLOS Sovereign EEZ Enforcement**:
   - **Code Assumption**: Inside sovereign EEZ, dark commercial hulls escalate to `HIGH` or `CRITICAL` threat tier.
   - **Maritime Law Audit**: Accurate under UNCLOS Articles 56, 73, and coastal state sovereign resource jurisdiction.

---

## 5. Corrective Recommendations

1. **Rename Metric**: Change `dark_vessel_probability` to `evidential_suspicion_score` or `dark_vessel_risk_index` across schemas and reports.
2. **Replace Piecewise Steps with Sigmoidal Logistic Curves**: Replace hard cliffs (e.g. at 100km or 12h) with continuous sigmoid transformations $S(x) = \frac{1}{1 + e^{-k(x - x_0)}}$ to ensure smooth gradient optimization.
