"""Matplotlib figures for the PDF dossier. Every function returns PNG bytes (or None when the
underlying data does not exist) — figures are never fabricated to fill a page."""

import io
import json
import math
import os
from typing import Any, Dict, List, Optional

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Rectangle  # noqa: E402

NAVY = "#0B1F3A"
CYAN = "#0891B2"
AMBER = "#D97706"
RED = "#DC2626"
GREEN = "#16A34A"
GREY = "#64748B"
PURPLE = "#7C3AED"

_EEZ_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw", "geospatial", "arabian_sea_eez.geojson"))


def _png(fig: "plt.Figure") -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return buf.getvalue()


def _db(a: np.ndarray) -> np.ndarray:
    return 10.0 * np.log10(np.clip(a, 1.0, None))


def _stretch(a: np.ndarray) -> np.ndarray:
    db = _db(a)
    lo, hi = np.percentile(db, [2, 98])
    return np.clip((db - lo) / max(hi - lo, 1e-6), 0, 1)


def chip_panels(chip: Any, detections: List[Dict[str, Any]], primary_id: Optional[str]) -> Optional[bytes]:
    """VV / VH / composite panels with detector boxes and the 15-px clutter annulus."""
    if chip is None:
        return None
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.7))
    panels = [("VV (dB stretch)", _stretch(chip.chip_vv), "gray"), ("VH (dB stretch)", _stretch(chip.chip_vh), "gray"), ("Dual-pol composite", chip.to_rgb_composite() / 255.0, None)]
    for ax, (title, img, cmap) in zip(axes, panels):
        ax.imshow(img, cmap=cmap, interpolation="nearest")
        ax.set_title(title, fontsize=9, color=NAVY)
        ax.set_xticks([]); ax.set_yticks([])
        for d in detections:
            if not d.get("bbox_pixel"):
                continue
            x1, y1, x2, y2 = d["bbox_pixel"]
            is_p = d.get("detection_id") == primary_id
            ax.add_patch(Rectangle((x1, y1), x2 - x1, y2 - y1, fill=False, ec=("#00E5FF" if is_p else "#F59E0B"), lw=1.2))
            if is_p:
                ax.add_patch(Rectangle((x1 - 15, y1 - 15), x2 - x1 + 30, y2 - y1 + 30, fill=False, ec="#F59E0B", lw=0.8, ls="--"))
    fig.suptitle("Real Sentinel-1 chip · cyan = target · amber = other detections / clutter guard", fontsize=8, color=GREY, y=0.02)
    return _png(fig)


def clutter_histogram(chip: Any, primary: Dict[str, Any]) -> Optional[bytes]:
    if chip is None or not primary.get("bbox_pixel"):
        return None
    vv = _db(chip.chip_vv)
    h, w = vv.shape
    x1, y1, x2, y2 = primary["bbox_pixel"]
    tmask = np.zeros((h, w), bool); tmask[max(0, y1):min(h, y2), max(0, x1):min(w, x2)] = True
    cmask = np.zeros((h, w), bool); cmask[max(0, y1 - 15):min(h, y2 + 15), max(0, x1 - 15):min(w, x2 + 15)] = True
    cmask &= ~tmask
    if not tmask.any() or not cmask.any():
        return None
    fig, ax = plt.subplots(figsize=(5.2, 2.8))
    ax.hist(vv[cmask], bins=40, alpha=0.65, color=AMBER, label=f"Clutter annulus (mean {vv[cmask].mean():.1f} dB)", density=True)
    ax.hist(vv[tmask], bins=40, alpha=0.65, color=CYAN, label=f"Target (mean {vv[tmask].mean():.1f} dB)", density=True)
    ax.set_xlabel("VV backscatter (dB, uncalibrated)", fontsize=8); ax.set_ylabel("Density", fontsize=8)
    ax.tick_params(labelsize=7); ax.legend(fontsize=7, frameon=False)
    ax.set_title("Target vs sea-clutter backscatter", fontsize=9, color=NAVY)
    return _png(fig)


def _km_to_deg(km: float, lat: float) -> tuple:
    return km / 111.32, km / (111.32 * max(math.cos(math.radians(lat)), 0.05))


def tactical_map(detection: Dict[str, Any], ais: Optional[Dict[str, Any]], geo: Dict[str, Any], waypoints: List[Dict[str, Any]],
                 gaps: List[Dict[str, Any]]) -> bytes:
    lat0, lon0 = detection["latitude"], detection["longitude"]
    in_cov = geo.get("in_coverage", True)
    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    pts_lat = [lat0] + [w["projected_lat"] for w in waypoints]
    pts_lon = [lon0] + [w["projected_lon"] for w in waypoints]

    if in_cov and os.path.exists(_EEZ_PATH):
        with open(_EEZ_PATH, "r", encoding="utf-8") as f:
            gj = json.load(f)
        palette = [CYAN, PURPLE, GREEN, AMBER]
        for i, feat in enumerate(gj.get("features", [])):
            geom = feat.get("geometry", {})
            if geom.get("type") != "Polygon":
                continue
            ring = np.array(geom["coordinates"][0])
            props = feat.get("properties", {})
            ax.fill(ring[:, 0], ring[:, 1], alpha=0.08, color=palette[i % 4])
            ax.plot(ring[:, 0], ring[:, 1], lw=1, color=palette[i % 4], ls="--", label=f"{props.get('sovereign', 'Zone')} {props.get('zone_type', '')}"[:48])
            pts_lat += list(ring[:, 1]); pts_lon += list(ring[:, 0])
        from src.geospatial.eez_checker import RealEEZChecker
        for z in RealEEZChecker.STS_ZONES:
            dlat, dlon = _km_to_deg(z["radius_km"], z["lat"])
            ax.add_patch(plt.matplotlib.patches.Ellipse((z["lon"], z["lat"]), 2 * dlon, 2 * dlat, fill=False, ec=RED, lw=0.9, ls=":"))
            ax.annotate(z["name"], (z["lon"], z["lat"]), fontsize=5.5, color=RED, ha="center")
    else:
        ax.text(0.02, 0.02, "No EEZ / STS layers: position is outside the bundled Arabian Sea dataset", transform=ax.transAxes, fontsize=7, color=GREY)

    for g in gaps or []:
        if g.get("end_lat") is not None:
            ax.plot([g["start_lon"], g["end_lon"]], [g["start_lat"], g["end_lat"]], color=AMBER, lw=1.6, ls="--")
            ax.scatter([g["start_lon"]], [g["start_lat"]], c=AMBER, s=18, marker="s")
            pts_lat += [g["start_lat"], g["end_lat"]]; pts_lon += [g["start_lon"], g["end_lon"]]
    if waypoints:
        ax.plot([lon0] + [w["projected_lon"] for w in waypoints], [lat0] + [w["projected_lat"] for w in waypoints], color=PURPLE, lw=1.4)
        for w in waypoints:
            dlat, dlon = _km_to_deg(w["uncertainty_radius_km"], w["projected_lat"])
            ax.add_patch(plt.matplotlib.patches.Ellipse((w["projected_lon"], w["projected_lat"]), 2 * dlon, 2 * dlat, fc=PURPLE, alpha=0.12, ec=PURPLE, lw=0.8))
            ax.annotate(f"+{w['projection_hours']:g} h", (w["projected_lon"], w["projected_lat"]), fontsize=6.5, color=PURPLE, xytext=(3, 3), textcoords="offset points")
    ax.scatter([lon0], [lat0], c=RED, s=60, zorder=5, label="SAR detection")
    if ais:
        ax.scatter([ais["longitude"]], [ais["latitude"]], c=GREEN, s=45, marker="^", zorder=5, label=f"AIS: {ais.get('vessel_name') or ais.get('mmsi')}")
        pts_lat.append(ais["latitude"]); pts_lon.append(ais["longitude"])

    span = 3.0 if in_cov else 0.6
    if in_cov:
        ax.set_xlim(min(pts_lon) - 1, max(pts_lon) + 1); ax.set_ylim(min(pts_lat) - 1, max(pts_lat) + 1)
    else:
        ax.set_xlim(min(pts_lon) - span, max(pts_lon) + span); ax.set_ylim(min(pts_lat) - span, max(pts_lat) + span)
    ax.set_aspect(1.0 / max(math.cos(math.radians(lat0)), 0.2))
    ax.grid(alpha=0.25, lw=0.5); ax.tick_params(labelsize=7)
    ax.set_xlabel("Longitude (°E)", fontsize=8); ax.set_ylabel("Latitude (°N)", fontsize=8)
    ax.legend(fontsize=6, loc="upper left", frameon=True, framealpha=0.85)
    ax.set_title("Tactical picture — target, AIS, forecast cones, jurisdiction layers", fontsize=9, color=NAVY)
    return _png(fig)


def schematic_hull(detection: Dict[str, Any]) -> bytes:
    """Clearly-labelled schematic for cases that have no real imagery."""
    fig, ax = plt.subplots(figsize=(4.8, 2.6))
    L, B = detection["length_m"], detection["width_m"]
    ax.add_patch(Rectangle((-L / 2, -B / 2), L, B, fc=CYAN, alpha=0.5, ec=NAVY))
    ax.add_patch(Rectangle((-L / 2 - 30, -B / 2 - 30), L + 60, B + 60, fill=False, ec=AMBER, ls="--", lw=0.9))
    ax.set_xlim(-L / 2 - 60, L / 2 + 60); ax.set_ylim(-max(B, 40) - 50, max(B, 40) + 50)
    ax.set_aspect("equal"); ax.tick_params(labelsize=6)
    ax.set_title(f"SCHEMATIC ONLY (no raw radar chip) · {L:.0f} m × {B:.0f} m", fontsize=8, color=RED)
    ax.set_xlabel("metres", fontsize=7)
    return _png(fig)


def sensitivity_curve(points: List[tuple], baseline: tuple) -> Optional[bytes]:
    if not points:
        return None
    xs, ys = zip(*points)
    fig, ax = plt.subplots(figsize=(5.2, 2.8))
    ax.plot(xs, ys, color=CYAN, lw=1.8)
    ax.axvline(30, color=GREY, ls=":", lw=0.9); ax.text(31, 0.02, "30 m SOLAS-style exemption line", fontsize=6, color=GREY)
    ax.scatter([baseline[0]], [baseline[1]], c=RED, zorder=5, s=36, label="This target")
    ax.axhline(0.70, color=RED, ls="--", lw=0.8); ax.text(xs[0], 0.715, "0.70 = dark-evasion threshold", fontsize=6, color=RED)
    ax.set_xlabel("Measured length (m)", fontsize=8); ax.set_ylabel("Dark-vessel probability", fontsize=8)
    ax.set_ylim(0, 1); ax.tick_params(labelsize=7); ax.legend(fontsize=7, frameon=False)
    ax.set_title("Sensitivity of the score to vessel length (all else equal)", fontsize=9, color=NAVY)
    return _png(fig)


def counterfactual_bars(rows: List[Dict[str, Any]]) -> Optional[bytes]:
    if not rows:
        return None
    fig, ax = plt.subplots(figsize=(6.2, 0.45 * len(rows) + 1.0))
    labels = [r["label"] for r in rows][::-1]
    vals = [r["probability"] for r in rows][::-1]
    colors = [RED if v >= 0.7 else (AMBER if v >= 0.4 else GREEN) for v in vals]
    ax.barh(labels, vals, color=colors)
    for i, v in enumerate(vals):
        ax.text(v + 0.01, i, f"{v:.2f}", va="center", fontsize=7)
    ax.axvline(0.70, color=RED, ls="--", lw=0.8); ax.axvline(0.40, color=AMBER, ls="--", lw=0.8)
    ax.set_xlim(0, 1.08); ax.tick_params(labelsize=7)
    ax.set_xlabel("Dark-vessel probability", fontsize=8)
    ax.set_title("Counterfactual re-scoring (same deterministic scorer)", fontsize=9, color=NAVY)
    return _png(fig)


_NODES = ["MissionController", "SARAISCorrelator", "FeatureEngineerNode", "SanctionsScreenerNode", "ForensicAssessorNode", "HumanReviewNode", "ReportPreparerNode"]
_STATUS_COLOR = {"SUCCESS": GREEN, "APPROVED": GREEN, "DEGRADED": AMBER, "FAILED": RED, "SKIPPED": GREY, "OVERRIDDEN": AMBER}


def workflow_diagram(trace: List[Dict[str, Any]]) -> bytes:
    status = {t["agent_name"]: t.get("status", "SUCCESS") for t in trace}
    fig, ax = plt.subplots(figsize=(10.5, 2.2))
    ax.set_xlim(0, 7.4); ax.set_ylim(0, 2.0); ax.axis("off")
    xs = [0.05 + i * 1.05 for i in range(7)]
    for i, name in enumerate(_NODES):
        run = name in status
        col = _STATUS_COLOR.get(status.get(name, ""), "#CBD5E1")
        ax.add_patch(FancyBboxPatch((xs[i], 0.8), 0.9, 0.7, boxstyle="round,pad=0.02", fc=col if run else "white", ec=NAVY if run else "#CBD5E1", alpha=0.85 if run else 1, lw=1))
        label = name.replace("Node", "").replace("SARAIS", "SAR-AIS\n").replace("Controller", "\nController").replace("Engineer", "\nEngineer").replace("Screener", "\nScreener").replace("Assessor", "\nAssessor").replace("Review", "\nReview").replace("Preparer", "\nPreparer")
        ax.text(xs[i] + 0.45, 1.15, f"{i + 1}\n{label}", ha="center", va="center", fontsize=5.8, color="white" if run else GREY)
        if i < 6:
            ax.add_patch(FancyArrowPatch((xs[i] + 0.92, 1.15), (xs[i + 1] - 0.02, 1.15), arrowstyle="-|>", mutation_scale=7, color=GREY, lw=0.8))
    if "HumanReviewNode" not in status:
        ax.text(xs[5] + 0.45, 0.55, "skipped: no human review required", ha="center", fontsize=5.5, color=GREY)
    ax.set_title("LangGraph execution path (green = success, amber = degraded, white = not executed)", fontsize=8, color=NAVY)
    return _png(fig)


def latency_chart(trace: List[Dict[str, Any]]) -> Optional[bytes]:
    rows = [(t["agent_name"], (t.get("details") or {}).get("latency_ms", t.get("latency_ms"))) for t in trace]
    rows = [(n, float(v)) for n, v in rows if v is not None]
    if not rows:
        return None
    fig, ax = plt.subplots(figsize=(6.0, 0.4 * len(rows) + 0.9))
    ax.barh([r[0] for r in rows][::-1], [r[1] for r in rows][::-1], color=CYAN)
    ax.set_xlabel("Wall-clock latency (ms)", fontsize=8); ax.tick_params(labelsize=7)
    ax.set_title("Per-node latency", fontsize=9, color=NAVY)
    return _png(fig)


def ais_gap_chart(gaps: List[Dict[str, Any]]) -> Optional[bytes]:
    if not gaps:
        return None
    fig, ax = plt.subplots(figsize=(6.0, 0.5 * len(gaps) + 1.0))
    ax.barh([f"Gap {i + 1}" for i in range(len(gaps))][::-1], [g["duration_hours"] for g in gaps][::-1],
            color=[RED if g.get("is_suspicious") else GREY for g in gaps][::-1])
    ax.axvline(12, color=AMBER, ls="--", lw=0.8); ax.text(12.2, -0.4, "12 h outage trigger", fontsize=6, color=AMBER)
    ax.set_xlabel("Duration (hours)", fontsize=8); ax.tick_params(labelsize=7)
    ax.set_title("AIS transmission gaps (red = flagged suspicious)", fontsize=9, color=NAVY)
    return _png(fig)
