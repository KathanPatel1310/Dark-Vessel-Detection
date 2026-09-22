"""Pillar 1: SAR Feature Engineering Module.
Extracts morphological, geometric, and radiometric features from radar detections.
All formulas are mathematically defined and traceable for academic ablation.
"""

import math
from typing import Optional
from src.schemas.sar import SARDetection
from src.schemas.features import SARFeatures

def compute_aspect_ratio(length_m: float, width_m: float) -> float:
    """Computes Length-to-Beam ratio (L/B). Standard commercial vessels typically range 4.5 to 8.5."""
    if width_m <= 0:
        return 0.0
    return round(length_m / width_m, 3)

def compute_target_clutter_ratio(target_mean_db: Optional[float], background_clutter_db: Optional[float]) -> Optional[float]:
    """
    Computes Target-to-Clutter Ratio (TCR) in dB.
    TCR = Mean_Target_Sigma0 (dB) - Background_Clutter_Sigma0 (dB)
    Higher TCR indicates high metallic reflection (steel hull) vs organic or sea noise.
    """
    if target_mean_db is None or background_clutter_db is None:
        return None
    return round(target_mean_db - background_clutter_db, 2)

def compute_eccentricity(length_m: float, width_m: float) -> float:
    """
    Computes equivalent ellipse eccentricity: e = sqrt(1 - (b/a)^2) where a=L/2, b=W/2.
    Elongated commercial hulls have eccentricity near 0.95-0.98.
    """
    if length_m <= 0 or width_m <= 0 or width_m > length_m:
        return 0.0
    ratio = width_m / length_m
    return round(math.sqrt(max(0.0, 1.0 - (ratio ** 2))), 4)

def compute_compactness(length_m: float, width_m: float, area_m2: Optional[float] = None) -> float:
    """
    Computes isoperimetric quotient / compactness: P^2 / (4 * pi * Area).
    Uses Ramanujan ellipse perimeter approximation if perimeter not directly provided.
    """
    a = length_m / 2.0
    b = width_m / 2.0
    # Approximate ellipse perimeter
    perimeter = math.pi * (3 * (a + b) - math.sqrt((3 * a + b) * (a + 3 * b)))
    effective_area = area_m2 if (area_m2 and area_m2 > 0) else (math.pi * a * b)
    if effective_area <= 0:
        return 1.0
    return round((perimeter ** 2) / (4 * math.pi * effective_area), 3)

def extract_sar_features(detection: SARDetection) -> SARFeatures:
    """
    Extracts explicit, deterministic SAR features from a SARDetection object.
    """
    aspect = compute_aspect_ratio(detection.length_m, detection.width_m)
    tcr = detection.target_clutter_ratio_db
    if tcr is None and detection.mean_backscatter_db is not None and detection.background_mean_db is not None:
        tcr = compute_target_clutter_ratio(detection.mean_backscatter_db, detection.background_mean_db)

    area = detection.area_m2 if detection.area_m2 else (detection.length_m * detection.width_m * 0.785)
    ecc = compute_eccentricity(detection.length_m, detection.width_m)
    compact = compute_compactness(detection.length_m, detection.width_m, area)

    return SARFeatures(
        length_m=detection.length_m,
        width_m=detection.width_m,
        aspect_ratio=aspect,
        detection_area_m2=round(area, 1),
        orientation_deg=detection.heading_deg,
        peak_backscatter_db=detection.peak_backscatter_db,
        mean_backscatter_db=detection.mean_backscatter_db,
        background_clutter_db=detection.background_mean_db,
        target_to_clutter_ratio_db=tcr,
        compactness=compact,
        eccentricity=ecc,
        incidence_angle_deg=detection.incidence_angle_deg,
        polarization_ratio=None,
    )
