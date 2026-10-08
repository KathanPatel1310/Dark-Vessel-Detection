"""Real-World Satellite SAR & AIS Multi-Modal Feature Ablation Study.
Evaluates Random Forest classification benchmarks trained on authentic Sentinel-1 radar pixels
and co-registered maritime telemetry across 4 distinct feature representation subsets.
"""

import json
import math
import os
import time
from typing import Dict, List, Any
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    roc_auc_score, average_precision_score, f1_score, accuracy_score,
    balanced_accuracy_score, brier_score_loss, roc_curve, precision_recall_curve
)

from src.data.sar_chip_loader import RealSARDatasetLoader, RealSARChip
from src.models.sar_detector import SARVesselDetector
from src.features.sar_features import extract_sar_features
from src.geospatial.eez_checker import RealEEZChecker
from src.utils.logger import setup_logger

logger = setup_logger("real_sar_ablation")


def run_real_ablation():
    logger.info("=== STARTING REAL SATELLITE SAR FEATURE ABLATION STUDY ===")
    loader = RealSARDatasetLoader()
    chips = loader.load_all_chips()
    logger.info(f"Loaded {len(chips)} authentic Sentinel-1 SAR chips from disk.")

    if len(chips) < 20:
        logger.warning("Fewer than 20 chips found. Downloading sample batch...")
        loader.download_sample_chips(count=50)
        chips = loader.load_all_chips()

    detector = SARVesselDetector()
    eez_checker = RealEEZChecker()

    records: List[Dict[str, Any]] = []
    logger.info("Executing deep learning detection & physical feature extraction on radar chips...")

    for idx, chip in enumerate(chips):
        dets = detector.detect_on_chip(chip)
        if not dets:
            # If no ship detected, skip or use background measurement
            continue

        best_det = max(dets, key=lambda d: d.confidence)
        geo_ctx = eez_checker.get_geo_context(chip.latitude, chip.longitude)

        # Ground-truth target: High-Risk Tanker Identification (ITU AIS Codes 80-89)
        # Represents crude and chemical tankers operating in Persian Gulf / Arabian Sea evasion corridors
        is_target = 1 if chip.vessel_type.startswith("8") else 0

        # 1. Raw measurements
        raw_feats = {
            "raw_length_m": best_det.length_m,
            "raw_width_m": best_det.width_m,
            "raw_tcr_db": best_det.target_clutter_ratio_db or 0.0,
            "raw_lat": chip.latitude,
            "raw_lon": chip.longitude,
            "raw_sog": chip.sog_knots,
        }

        # 2. SAR physics engineered features
        sar_eng = {
            "sar_aspect_ratio": best_det.aspect_ratio,
            "sar_area_m2": best_det.area_m2 or (best_det.length_m * best_det.width_m),
            "sar_peak_backscatter_db": best_det.peak_backscatter_db or 0.0,
            "sar_mean_backscatter_db": best_det.mean_backscatter_db or 0.0,
            "sar_target_clutter_ratio_db": best_det.target_clutter_ratio_db or 0.0,
            "sar_confidence": best_det.confidence,
        }

        # 3. Geospatial & sovereignty features
        geo_eng = {
            "geo_distance_to_shore_km": geo_ctx.distance_to_coast_km,
            "geo_inside_eez": 1.0 if geo_ctx.inside_eez else 0.0,
            "geo_distance_to_eez_km": geo_ctx.distance_to_eez_boundary_km,
            "geo_distance_to_sts_km": geo_ctx.distance_to_sts_zone_km or 200.0,
            "geo_distance_to_port_km": geo_ctx.distance_to_nearest_port_km or 100.0,
        }

        record = {"target_is_tanker": is_target}
        record.update(raw_feats)
        record.update(sar_eng)
        record.update(geo_eng)
        records.append(record)

    df = pd.DataFrame(records)
    logger.info(f"Engineered feature matrix constructed: {df.shape[0]} samples, {df.shape[1] - 1} features.")
    logger.info(f"Target Tanker Distribution (ITU 80-89): {df['target_is_tanker'].value_counts().to_dict()}")

    y = df["target_is_tanker"].values

    subsets = {
        "Raw Sensor Only": [c for c in df.columns if c.startswith("raw_")],
        "SAR Physics Only": [c for c in df.columns if c.startswith("sar_")],
        "Geospatial EEZ Only": [c for c in df.columns if c.startswith("geo_")],
        "Combined Multi-Modal": [c for c in df.columns if c not in ["target_is_tanker"]],
    }

    results: Dict[str, Any] = {}
    roc_curves: Dict[str, Any] = {}
    pr_curves: Dict[str, Any] = {}
    feature_importances: Dict[str, float] = {}

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    for name, cols in subsets.items():
        X = df[cols].values
        clf = RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42, class_weight="balanced")

        probs = cross_val_predict(clf, X, y, cv=cv, method="predict_proba")[:, 1]
        preds = (probs >= 0.5).astype(int)

        roc_auc = roc_auc_score(y, probs)
        pr_auc = average_precision_score(y, probs)
        f1 = f1_score(y, preds, zero_division=0)
        acc = accuracy_score(y, preds)
        bal_acc = balanced_accuracy_score(y, preds)
        brier = brier_score_loss(y, probs)

        results[name] = {
            "feature_count": len(cols),
            "roc_auc": round(float(roc_auc), 4),
            "pr_auc": round(float(pr_auc), 4),
            "f1_score": round(float(f1), 4),
            "accuracy": round(float(acc), 4),
            "balanced_accuracy": round(float(bal_acc), 4),
            "brier_score": round(float(brier), 4),
        }
        logger.info(f"[{name}] ROC-AUC: {roc_auc:.4f} | PR-AUC: {pr_auc:.4f} | F1: {f1:.4f}")

        fpr, tpr, _ = roc_curve(y, probs)
        prec, rec, _ = precision_recall_curve(y, probs)
        roc_curves[name] = (fpr, tpr, roc_auc)
        pr_curves[name] = (rec, prec, pr_auc)

        if name == "Combined Multi-Modal":
            clf.fit(X, y)
            for col_name, imp in zip(cols, clf.feature_importances_):
                feature_importances[col_name] = round(float(imp), 4)

    # Plot ROC Curves
    plt.figure(figsize=(9, 7))
    for name, (fpr, tpr, auc_val) in roc_curves.items():
        plt.plot(fpr, tpr, lw=2, label=f"{name} (AUC = {auc_val:.3f})")
    plt.plot([0, 1], [0, 1], color="navy", lw=1.5, linestyle="--")
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel("False Positive Rate", fontsize=11)
    plt.ylabel("True Positive Rate", fontsize=11)
    plt.title("Real Satellite SAR Multi-Modal ROC Curves (Tanker vs Cargo/Other)", fontsize=13, fontweight="bold")
    plt.legend(loc="lower right")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    os.makedirs("reports/figures", exist_ok=True)
    os.makedirs("outputs/workflow_images", exist_ok=True)
    plt.savefig("reports/figures/real_feature_ablation_roc.png", dpi=150)
    plt.savefig("outputs/workflow_images/real_feature_ablation_roc.png", dpi=150)
    plt.close()

    # Plot Feature Importance Bar Chart
    sorted_imps = sorted(feature_importances.items(), key=lambda x: x[1], reverse=True)[:10]
    plt.figure(figsize=(10, 6))
    bars = plt.barh([x[0] for x in sorted_imps][::-1], [x[1] for x in sorted_imps][::-1], color="#2b5c8f")
    plt.xlabel("Gini Feature Importance", fontsize=11)
    plt.title("Top 10 Empirical Feature Importances (Real Sentinel-1 & AIS)", fontsize=13, fontweight="bold")
    plt.grid(True, alpha=0.3, axis="x")
    plt.tight_layout()
    plt.savefig("reports/figures/real_feature_importance.png", dpi=150)
    plt.savefig("outputs/workflow_images/real_feature_importance.png", dpi=150)
    plt.close()

    out_json = "reports/real_feature_ablation_results.json"
    with open(out_json, "w") as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "task_description": "Identification of High-Risk Tankers (Crude/Chemical Carriers) from Sentinel-1 SAR pixels & AIS",
            "total_real_chips_analyzed": len(records),
            "subsets": results,
            "feature_importances": feature_importances,
        }, f, indent=2)
    logger.info(f"Saved real ablation benchmark report to {out_json}")
    return results


if __name__ == "__main__":
    run_real_ablation()
