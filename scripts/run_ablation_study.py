"""
Phase 5: Feature Engineering Ablation Study.
Evaluates the predictive utility of raw vs. engineered feature subsets
on the dark vessel detection classification task.
"""

import json
import math
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, precision_score,
    recall_score, f1_score, roc_auc_score, average_precision_score,
    confusion_matrix, brier_score_loss, roc_curve, precision_recall_curve
)
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

from src.schemas.sar import SARDetection
from src.features.sar_features import extract_sar_features
from src.geospatial.eez_checker import RealEEZChecker

def run_ablation():
    print("=== STARTING PHASE 5 FEATURE ABLATION STUDY ===")
    sar_path = "data/raw/sar/real_sar_detections.csv"
    if not os.path.exists(sar_path):
        raise FileNotFoundError(f"Missing {sar_path}")
        
    df_raw = pd.read_csv(sar_path)
    print(f"Loaded {len(df_raw)} records from {sar_path}")
    
    # Target label: Dark vessel (no AIS match)
    # Target distribution
    target = (~df_raw["matched_ais"]).astype(int)
    print(f"Target distribution: {target.value_counts().to_dict()} (Dark rate: {target.mean():.4f})")
    
    # Subsample 10,000 records for fast, reliable cross-validated ablation
    sample_df = df_raw.sample(n=min(10000, len(df_raw)), random_state=42).reset_index(drop=True)
    y = (~sample_df["matched_ais"]).astype(int).values
    
    eez_checker = RealEEZChecker()
    
    # Extract feature representations
    print("Extracting engineered features across domains...")
    sar_feats_list = []
    geo_feats_list = []
    raw_feats_list = []
    
    for _, row in sample_df.iterrows():
        # Raw features
        raw_feats_list.append({
            "raw_length_m": float(row["vessel_length_m"]),
            "raw_width_m": float(row["vessel_width_m"]),
            "raw_heading_deg": float(row["heading_deg"]),
            "raw_distance_shore_km": float(row["distance_from_shore_km"]),
            "raw_tcr_db": float(row["target_clutter_ratio_db"]),
            "raw_lat": float(row["detect_lat"]),
            "raw_lon": float(row["detect_lon"])
        })
        
        # SAR engineered
        sar_det = SARDetection(
            detection_id=row["detect_id"],
            scene_id=row["scene_id"],
            timestamp=pd.to_datetime(row["timestamp"]).to_pydatetime(),
            latitude=float(row["detect_lat"]),
            longitude=float(row["detect_lon"]),
            length_m=float(row["vessel_length_m"]),
            width_m=float(row["vessel_width_m"]),
            aspect_ratio=float(row["aspect_ratio"]),
            confidence=0.9 if row["confidence"] == "HIGH" else 0.6,
            heading_deg=float(row["heading_deg"]),
            target_clutter_ratio_db=float(row["target_clutter_ratio_db"])
        )
        sar_eng = extract_sar_features(sar_det)
        sar_feats_list.append({
            "sar_aspect_ratio": sar_eng.aspect_ratio,
            "sar_area_m2": sar_eng.detection_area_m2,
            "sar_compactness": sar_eng.compactness,
            "sar_eccentricity": sar_eng.eccentricity,
            "sar_tcr_db": sar_eng.target_to_clutter_ratio_db or 0.0,
            "sar_length_m": sar_eng.length_m
        })
        
        # Geo engineered
        geo_ctx = eez_checker.get_geo_context(float(row["detect_lat"]), float(row["detect_lon"]))
        geo_feats_list.append({
            "geo_inside_eez": 1.0 if geo_ctx.inside_eez else 0.0,
            "geo_dist_eez_border_km": geo_ctx.distance_to_eez_boundary_km,
            "geo_dist_coast_km": geo_ctx.distance_to_coast_km,
            "geo_dist_nearest_port_km": geo_ctx.distance_to_nearest_port_km,
            "geo_dist_sts_zone_km": geo_ctx.distance_to_sts_zone_km or 999.0
        })

    df_raw_feat = pd.DataFrame(raw_feats_list)
    df_sar_feat = pd.DataFrame(sar_feats_list)
    df_geo_feat = pd.DataFrame(geo_feats_list)
    df_all_eng = pd.concat([df_sar_feat, df_geo_feat], axis=1)
    df_all_combined = pd.concat([df_raw_feat, df_sar_feat, df_geo_feat], axis=1)

    feature_sets = {
        "A_Raw_Inputs_Only": df_raw_feat,
        "B_SAR_Engineered_Only": df_sar_feat,
        "C_Geospatial_Engineered_Only": df_geo_feat,
        "D_All_Engineered_SAR_Geo": df_all_eng,
        "E_All_Features_Combined": df_all_combined,
        "F_All_Excluding_SAR_Morphology": df_all_combined.drop(columns=["sar_aspect_ratio", "sar_compactness", "sar_eccentricity", "sar_area_m2"]),
        "G_All_Excluding_Geospatial": df_all_combined.drop(columns=df_geo_feat.columns)
    }

    # Train/Validation/Test split: 70% train, 15% val, 15% test
    indices = np.arange(len(y))
    train_idx, test_idx, y_train, y_test = train_test_split(indices, y, test_size=0.30, random_state=42, stratify=y)
    val_idx, test_idx, y_val, y_test = train_test_split(test_idx, y_test, test_size=0.50, random_state=42, stratify=y_test)

    print(f"Data Splits: Train={len(train_idx)}, Val={len(val_idx)}, Test={len(test_idx)}")

    ablation_results = {}
    roc_curves = {}

    for name, feat_df in feature_sets.items():
        print(f"\n--- Evaluating Feature Set: {name} ({feat_df.shape[1]} features) ---")
        X_train = feat_df.iloc[train_idx].values
        X_val = feat_df.iloc[val_idx].values
        X_test = feat_df.iloc[test_idx].values

        clf = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42, class_weight="balanced")
        clf.fit(X_train, y_train)

        y_pred = clf.predict(X_test)
        y_prob = clf.predict_proba(X_test)[:, 1]

        acc = accuracy_score(y_test, y_pred)
        bal_acc = balanced_accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        roc_auc = roc_auc_score(y_test, y_prob)
        pr_auc = average_precision_score(y_test, y_prob)
        brier = brier_score_loss(y_test, y_prob)
        cm = confusion_matrix(y_test, y_pred).tolist()

        fpr, tpr, _ = roc_curve(y_test, y_prob)
        roc_curves[name] = {"fpr": fpr.tolist(), "tpr": tpr.tolist(), "auc": roc_auc}

        metrics = {
            "num_features": feat_df.shape[1],
            "feature_names": list(feat_df.columns),
            "accuracy": round(float(acc), 4),
            "balanced_accuracy": round(float(bal_acc), 4),
            "precision": round(float(prec), 4),
            "recall": round(float(rec), 4),
            "f1_score": round(float(f1), 4),
            "roc_auc": round(float(roc_auc), 4),
            "pr_auc": round(float(pr_auc), 4),
            "brier_score": round(float(brier), 4),
            "confusion_matrix": cm
        }
        ablation_results[name] = metrics
        print(f"  Accuracy: {acc:.4f} | BalAcc: {bal_acc:.4f} | F1: {f1:.4f} | ROC-AUC: {roc_auc:.4f} | PR-AUC: {pr_auc:.4f}")

    # Save JSON results
    os.makedirs("reports/figures", exist_ok=True)
    with open("reports/feature_ablation_results.json", "w") as f:
        json.dump(ablation_results, f, indent=2)
    print("Saved reports/feature_ablation_results.json")

    # Plot ROC Curves
    plt.figure(figsize=(10, 7))
    for name, rdata in roc_curves.items():
        plt.plot(rdata["fpr"], rdata["tpr"], label=f"{name} (AUC={rdata['auc']:.3f})")
    plt.plot([0, 1], [0, 1], 'k--', alpha=0.5, label="Random Guess")
    plt.xlabel("False Positive Rate", fontsize=11)
    plt.ylabel("True Positive Rate", fontsize=11)
    plt.title("Receiver Operating Characteristic (ROC) - Feature Ablation Study", fontsize=13, fontweight='bold')
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend(loc="lower right", fontsize=9)
    plt.tight_layout()
    plt.savefig("reports/figures/feature_ablation_roc.png", dpi=300)
    plt.close()
    print("Saved reports/figures/feature_ablation_roc.png")

    # Feature Importance for All Combined
    X_train_all = df_all_combined.iloc[train_idx].values
    clf_all = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42, class_weight="balanced")
    clf_all.fit(X_train_all, y_train)
    importances = clf_all.feature_importances_
    feat_names = list(df_all_combined.columns)
    sorted_idx = np.argsort(importances)[::-1]

    plt.figure(figsize=(10, 6))
    plt.barh([feat_names[i] for i in sorted_idx[:12]][::-1], [importances[i] for i in sorted_idx[:12]][::-1], color="#1f77b4")
    plt.xlabel("Gini Feature Importance", fontsize=11)
    plt.title("Top Feature Importances (Random Forest)", fontsize=13, fontweight='bold')
    plt.grid(axis="x", linestyle="--", alpha=0.6)
    plt.tight_layout()
    plt.savefig("reports/figures/feature_importance.png", dpi=300)
    plt.close()
    print("Saved reports/figures/feature_importance.png")

if __name__ == "__main__":
    run_ablation()
