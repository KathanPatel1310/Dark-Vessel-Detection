# Phase 4 Feature Engineering Mathematical and Empirical Validation Report

**Execution Timestamp**: 2026-09-26T22:34:25+05:30  
**Audit Script**: `scripts/validate_feature_math.py`  
**Target Codebase**: `src/features/` (`sar_features.py`, `ais_features.py`, `geospatial_features.py`, `fusion_features.py`, `pipeline.py`)  

---

## 1. Mathematical Formulas, Units, and Ranges by Domain

### A. SAR Morphology and Radiometry (`src/features/sar_features.py`)

| Feature | Formula | Units | Range | Missing-Value Behavior | Numerical Stability Safeguard |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Aspect Ratio ($L/B$)** | $\frac{L}{W}$ | Dimensionless | $[0.0, \infty)$ | Defaults to `0.0` if $W \le 0$ | Checked with `if width_m <= 0: return 0.0` |
| **Target-to-Clutter Ratio (TCR)** | $\sigma^0_{\text{target}} - \sigma^0_{\text{clutter}}$ | Decibels (dB) | $(-\infty, \infty)$, typical $[5, 35]$ | Returns `None` if clutter is absent | Handled via nullable float check |
| **Equivalent Ellipse Eccentricity ($e$)** | $\sqrt{\max\left(0, 1 - \left(\frac{W}{L}\right)^2\right)}$ | Dimensionless | $[0.0, 1.0)$ | Defaults to `0.0` if $L \le 0$ or $W > L$ | Clamped via `max(0.0, 1.0 - ratio^2)` |
| **Isoperimetric Compactness ($C$)** | $\frac{P^2}{4 \pi A}$ (Ramanujan ellipse perimeter $P$) | Dimensionless | $[1.0, \infty)$ | Defaults to `1.0` if area $\le 0$ | Checked with `if effective_area <= 0: return 1.0` |
| **Radar Area Footprint ($A$)** | $L \times W \times 0.785$ (or direct mask) | Square meters ($m^2$) | $[0.0, \infty)$ | Reconstructed from bounding box | Elliptic factor approximation $0.785 \approx \frac{\pi}{4}$ |

### B. AIS Kinematics and Forensics (`src/features/ais_features.py`)

| Feature | Formula | Units | Range | Missing-Value Behavior | Numerical Stability Safeguard |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Mean Speed Over Ground (SOG)** | $\frac{1}{N}\sum v_i$ | Knots | $[0.0, 100.0]$ | Defaults to `0.0` if $N=0$ | Handled via empty list branch |
| **SOG Variance** | $\frac{1}{N}\sum (v_i - \bar{v})^2$ | $\text{knots}^2$ | $[0.0, \infty)$ | Defaults to `0.0` if $N < 2$ | Protected against Bessel correction crash |
| **Circular Heading Variance** | $1 - \sqrt{\bar{\cos\theta}^2 + \bar{\sin\theta}^2}$ | Dimensionless | $[0.0, 1.0]$ | Defaults to `0.0` if $N < 2$ | Clamped via `min(1.0, R)` to avoid negative variance |
| **Trajectory Curvature / Tortuosity** | $\frac{\sum d_{\text{step}}}{d_{\text{endpoints}}}$ | Dimensionless | $[1.0, \infty)$ | Defaults to `1.0` if stationary | If $d_{\text{endpoints}} \le 0.1\text{km}$, clamps denominator to $0.1$ |
| **Current AIS Outage Duration** | $t_{\text{SAR}} - t_{\text{last AIS}}$ | Hours | $[0.0, \infty)$ | Defaults to `48.0` hrs if vessel is dark | Validated positive time delta |
| **Historical 30-Day Gaps** | Count of gaps $\ge 2.0$ hrs | Count | $[0, \infty)$ | Defaults to `0` if no gap logs exist | Null-safe list comprehension |

### C. Geospatial and Sovereignty (`src/features/geospatial_features.py`)

| Feature | Formula | Units | Range | Missing-Value Behavior | Numerical Stability Safeguard |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Distance to Sovereign Coastline** | $\min_k \text{Haversine}(p, c_k)$ | Kilometers (km) | $[0.0, 20000]$ | Real coastal vertices | Validated spherical Haversine formula |
| **Distance to Nearest Port** | $\min_p \text{Haversine}(p, \text{port}_p)$ | Kilometers (km) | $[0.0, 20000]$ | 7 major regional ports | Deterministic lookup table |
| **Distance to STS Transfer Corridor**| $\min_s \text{Haversine}(p, \text{zone}_s)$ | Kilometers (km) | $[0.0, 20000]$ | 3 high-risk STS sectors | Deterministic lookup table |
| **Inside Sovereign EEZ** | Shapely `contains(Point(lon, lat))` | Boolean | `{True, False}` | Defaults to `False` if outside | 3 real UNCLOS EEZ polygons (India, Pakistan, Oman) |
| **Distance to Sovereign EEZ Border** | Boundary distance in km | Kilometers (km) | $[0.0, \infty)$ | Computed via centroid buffer | Projected approximation |

### D. SAR-AIS Spatio-Temporal Fusion (`src/features/fusion_features.py`)

| Feature | Formula | Units | Range | Missing-Value Behavior | Numerical Stability Safeguard |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Spatial Discrepancy** | $\text{Haversine}(p_{\text{SAR}}, p_{\text{AIS}})$ | Kilometers (km) | $[0.0, 20000]$ | Defaults to `999.0` km if dark | Handled via nullable AIS observation |
| **Temporal Discrepancy** | $|t_{\text{SAR}} - t_{\text{AIS}}| / 60$ | Minutes | $[0.0, \infty)$ | Defaults to `9999.0` min if dark | Handled via nullable AIS observation |
| **Heading Discrepancy** | Folded difference mod $180^\circ$ | Degrees | $[0.0, 90.0]$ | Returns `None` if dark | Resolves $180^\circ$ radar bow/stern ambiguity |
| **Speed Consistency Score** | $\max(0.0, 1 - \frac{d}{20\text{km}})$ | Dimensionless | $[0.0, 1.0]$ | Defaults to `0.0` if dark | Clamped to non-negative range |
| **Candidate Identity Score** | $0.5 S_{\text{spatial}} + 0.3 S_{\text{temporal}} + 0.2 S_{\text{dim}}$ | Dimensionless | $[0.0, 1.0]$ | Defaults to `0.0` if uncorrelated | Linear weighted combination |

---

## 2. Empirical Edge Case Audit Results

All tests below were empirically executed using `scripts/validate_feature_math.py`.

```text
=== FEATURE MATH & EDGE CASE AUDIT RESULTS ===
  determinism_exact_match: True
  total_flattened_features: 42
  missing_ais_spatial_discrepancy: 999.0
  missing_ais_temporal_difference: 9999.0
  missing_ais_is_correlated: False
  missing_ais_gap_hours: 48.0
  missing_ais_sog_mean: 0.0
  stationary_sog_mean: 0.0
  stationary_sog_variance: 0.0
  stationary_heading_variance: 0.0
  stationary_curvature: 1.0
  sar_length_15m_aspect_ratio: 1.5
  sar_length_15m_area: 117.8
  sar_length_15m_compactness: 1.063
  sar_length_15m_eccentricity: 0.7454
  sar_length_30m_aspect_ratio: 3.0
  sar_length_30m_area: 235.5
  sar_length_30m_compactness: 1.509
  sar_length_30m_eccentricity: 0.9428
  sar_length_99m_aspect_ratio: 9.99
  sar_length_99m_area: 784.2
  sar_length_99m_compactness: 4.175
  sar_length_99m_eccentricity: 0.995
  sar_length_100m_aspect_ratio: 10.0
  sar_length_100m_area: 785.0
  sar_length_100m_compactness: 4.179
  sar_length_100m_eccentricity: 0.995
  sar_length_350m_aspect_ratio: 35.0
  sar_length_350m_area: 2747.5
  sar_length_350m_compactness: 14.173
  sar_length_350m_eccentricity: 0.9996
  antimeridian_spatial_discrepancy_km: 10.95
  antimeridian_is_correlated: False
  polar_spatial_discrepancy_km: 1.11
  zero_width_aspect_ratio: 0.0
  zero_width_eccentricity: 0.0
  zero_width_compactness: 1.0
  long_gap_hours: 504.0
  long_gap_count: 1
  has_future_leakage: False
  has_target_label_leakage: False
```

---

## 3. Findings on Feature Integrity and Stability

1. **Determinism**: 
   - Repeated calls with identical inputs generate byte-identical feature vectors (verified `vec1 == vec2`).
2. **Future Leakage**:
   - Verified that no feature vector field references future timestamps, dead-reckoning extrapolation waypoints, or future mission states.
3. **Target Label Leakage**:
   - The feature vector contains 42 raw and derived kinematic/morphological measurements. It **does not** contain downstream heuristic targets (`deliberate_dark`, `risk_score`, `threat_tier`, `is_sanctioned`).
4. **Antimeridian & Polar Stability**:
   - The haversine implementation in `eez_checker.py` handles the antimeridian boundary correctly ($10.95$ km for points at $179.95^\circ\text{E}$ and $-179.95^\circ\text{W}$ at latitude $10^\circ$) due to the periodicity of $\sin^2(\Delta \lambda / 2)$.
   - Polar coordinates ($89.0^\circ\text{N}$ vs $89.01^\circ\text{N}$) compute to $1.11$ km without floating-point divergence.
5. **Zero Width & Zero Length Edge Cases**:
   - Handled via defensive conditionals (`width_m <= 0`), returning standard fallbacks ($AR=0.0, e=0.0, C=1.0$) rather than throwing `ZeroDivisionError` or `ValueError` in `math.sqrt`.
