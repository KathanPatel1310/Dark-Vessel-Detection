"""Figures for the dossier, drawn in the report's editorial style: white page, navy ink, hairline
grids, one accent colour. Every function returns PNG bytes, or None when the underlying data does not
exist — figures are never fabricated to fill a page."""

import io
import json
import math
import os
from typing import Any, Dict, List, Optional, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.patches import Ellipse, Rectangle  # noqa: E402

INK = "#000000"
NAVY = "#2B2B2B"
ACCENT = "#000000"
MUTED = "#555555"
GRID = "#C8C8C8"
LAND = "#F2F2F2"
FAINT = "#EDEDED"


plt.rcParams.update({
    "font.family": ["DejaVu Serif"], "font.size": 7.5, "text.color": INK, "axes.labelcolor": MUTED,
    "axes.edgecolor": "#444444", "axes.linewidth": 0.6, "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelsize": 6.5,
    "ytick.labelsize": 6.5, "axes.spines.top": True, "axes.spines.right": True, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.5, "axes.axisbelow": True, "legend.frameon": False, "legend.fontsize": 6.8,
    "savefig.facecolor": "white", "figure.facecolor": "white",
})

_EEZ_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw", "geospatial", "arabian_sea_eez.geojson"))


def _png(fig: "plt.Figure") -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)
    return buf.getvalue()


def _db(a: np.ndarray) -> np.ndarray:
    return 10.0 * np.log10(np.clip(a, 1.0, None))


def _stretch(a: np.ndarray) -> np.ndarray:
    db = _db(a)
    lo, hi = np.percentile(db, [2, 98])
    return np.clip((db - lo) / max(hi - lo, 1e-6), 0, 1)


def _km_to_deg(km: float, lat: float) -> Tuple[float, float]:
    return km / 111.32, km / (111.32 * max(math.cos(math.radians(lat)), 0.05))


# ----------------------------------------------------------------------------------------------
def chip_panels(chip: Any, detections: List[Dict[str, Any]], primary_id: Optional[str]) -> Optional[bytes]:
    if chip is None:
        return None
    fig, axes = plt.subplots(1, 3, figsize=(7.0, 2.55))
    panels = [("VV", _stretch(chip.chip_vv), "gray"), ("VH", _stretch(chip.chip_vh), "gray"), ("Dual-pol composite", chip.to_rgb_composite() / 255.0, None)]
    for ax, (title, img, cmap) in zip(axes, panels):
        ax.imshow(img, cmap=cmap, interpolation="nearest")
        ax.set_title(title, fontsize=7, color=MUTED, loc="left", pad=3)
        ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
        for s in ax.spines.values():
            s.set_visible(True); s.set_color(GRID)
        for d in detections:
            if not d.get("bbox_pixel"):
                continue
            x1, y1, x2, y2 = d["bbox_pixel"]
            is_p = d.get("detection_id") == primary_id
            ax.add_patch(Rectangle((x1 - 3, y1 - 3), x2 - x1 + 6, y2 - y1 + 6, fill=False, ec=(ACCENT if is_p else "#FFFFFF"), lw=(1.3 if is_p else 0.7)))
            if is_p:
                ax.add_patch(Rectangle((x1 - 15, y1 - 15), x2 - x1 + 30, y2 - y1 + 30, fill=False, ec=ACCENT, lw=0.6, ls=(0, (3, 2))))
    fig.tight_layout(w_pad=0.6)
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
    fig, ax = plt.subplots(figsize=(3.4, 2.0))
    ax.hist(vv[cmask], bins=36, color="#B9C3CD", label=f"Sea clutter, mean {vv[cmask].mean():.1f} dB", density=True)
    ax.hist(vv[tmask], bins=36, color=ACCENT, alpha=0.85, label=f"Target, mean {vv[tmask].mean():.1f} dB", density=True)
    ax.set_xlabel("VV backscatter (dB, uncalibrated)", fontsize=6.8); ax.set_yticks([])
    ax.legend(loc="upper right")
    return _png(fig)


def tactical_map(detection: Dict[str, Any], ais: Optional[Dict[str, Any]], geo: Dict[str, Any], waypoints: List[Dict[str, Any]],
                 gaps: List[Dict[str, Any]]) -> bytes:
    lat0, lon0 = detection["latitude"], detection["longitude"]
    in_cov = geo.get("in_coverage", True)
    fig, ax = plt.subplots(figsize=(7.0, 3.9))
    ax.set_facecolor(LAND)
    lats, lons = [lat0], [lon0]
    for w in waypoints:
        lats.append(w["projected_lat"]); lons.append(w["projected_lon"])

    if in_cov and os.path.exists(_EEZ_PATH):
        with open(_EEZ_PATH, "r", encoding="utf-8") as f:
            gj = json.load(f)
        for feat in gj.get("features", []):
            geom = feat.get("geometry", {})
            if geom.get("type") != "Polygon":
                continue
            ring = np.array(geom["coordinates"][0])
            ax.fill(ring[:, 0], ring[:, 1], fc="#FFFFFF", ec=NAVY, lw=0.6, ls=(0, (4, 3)), alpha=0.85)
            props = feat.get("properties", {})
            ax.annotate(props.get("sovereign", ""), (ring[:, 0].mean(), ring[:, 1].mean()), fontsize=6.5, color=MUTED, ha="center")
            lats += list(ring[:, 1]); lons += list(ring[:, 0])
        from src.geospatial.eez_checker import RealEEZChecker
        for z in RealEEZChecker.STS_ZONES:
            dlat, dlon = _km_to_deg(z["radius_km"], z["lat"])
            ax.add_patch(Ellipse((z["lon"], z["lat"]), 2 * dlon, 2 * dlat, fill=False, ec=ACCENT, lw=0.6, ls=(0, (1, 2))))
    else:
        ax.text(0.02, 0.04, "No jurisdiction layers: this position is outside the bundled Arabian Sea dataset.", transform=ax.transAxes, fontsize=6.8, color=MUTED)

    for g in gaps or []:
        if g.get("end_lat") is not None:
            ax.plot([g["start_lon"], g["end_lon"]], [g["start_lat"], g["end_lat"]], color=NAVY, lw=1.1, ls=(0, (4, 2)))
            ax.scatter([g["start_lon"]], [g["start_lat"]], s=10, c=NAVY, marker="s", zorder=4)
            lats += [g["start_lat"], g["end_lat"]]; lons += [g["start_lon"], g["end_lon"]]
    if waypoints:
        ax.plot([lon0] + [w["projected_lon"] for w in waypoints], [lat0] + [w["projected_lat"] for w in waypoints], color=NAVY, lw=1.0, ls=(0, (2, 2)), zorder=3)
        for w in waypoints:
            dlat, dlon = _km_to_deg(w["uncertainty_radius_km"], w["projected_lat"])
            ax.add_patch(Ellipse((w["projected_lon"], w["projected_lat"]), 2 * dlon, 2 * dlat, fc=NAVY, alpha=0.08, ec=NAVY, lw=0.5, hatch="////"))
            ax.annotate(f"+{w['projection_hours']:g} h", (w["projected_lon"], w["projected_lat"]), fontsize=6.3, color=NAVY, xytext=(4, 4), textcoords="offset points")
    if ais:
        ax.scatter([ais["longitude"]], [ais["latitude"]], s=26, c=NAVY, marker="^", zorder=5, label=f"AIS position ({ais.get('vessel_name') or ais.get('mmsi')})")
        lats.append(ais["latitude"]); lons.append(ais["longitude"])
    ax.scatter([lon0], [lat0], s=46, c=ACCENT, zorder=6, edgecolors="white", linewidths=0.8, label="Radar detection")

    # Fit the extent to a wide frame so the plot fills the figure instead of leaving blank margins.
    pad = 1.0 if in_cov else 0.35
    ratio = 7.0 / 3.5
    coslat = max(math.cos(math.radians(lat0)), 0.2)
    cy, cx = (min(lats) + max(lats)) / 2.0, (min(lons) + max(lons)) / 2.0
    half_y = max((max(lats) - min(lats)) / 2.0 + pad, 0.3)
    half_x = max((max(lons) - min(lons)) / 2.0 + pad, 0.3)
    half_y = max(half_y, half_x * coslat / ratio)          # widen vertically if the track is wide
    half_x = max(half_x, half_y * ratio / coslat)          # widen horizontally to fill the frame
    ax.set_xlim(cx - half_x, cx + half_x); ax.set_ylim(cy - half_y, cy + half_y)
    ax.set_aspect(1.0 / coslat, adjustable="box")
    ax.set_xlabel("Longitude (°E)", fontsize=6.8); ax.set_ylabel("Latitude (°N)", fontsize=6.8)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=3)
    for s in ax.spines.values():
        s.set_visible(True); s.set_color(GRID)
    return _png(fig)


def schematic_hull(detection: Dict[str, Any]) -> bytes:
    fig, ax = plt.subplots(figsize=(3.6, 1.9))
    L, B = detection["length_m"], detection["width_m"]
    ax.add_patch(Rectangle((-L / 2, -B / 2), L, B, fc=NAVY, alpha=0.75, ec=NAVY))
    ax.add_patch(Rectangle((-L / 2 - 30, -B / 2 - 30), L + 60, B + 60, fill=False, ec=ACCENT, ls=(0, (3, 2)), lw=0.7))
    ax.set_xlim(-L / 2 - 60, L / 2 + 60); ax.set_ylim(-max(B, 40) - 50, max(B, 40) + 50)
    ax.set_aspect("equal"); ax.set_xlabel("metres", fontsize=6.8)
    ax.set_title(f"Schematic, not imagery · {L:.0f} × {B:.0f} m", fontsize=7, color=ACCENT, loc="left")
    return _png(fig)


def score_bars(rows: List[Dict[str, Any]], threshold: float = 0.70) -> Optional[bytes]:
    """Cumulative score after each rule, as horizontal bars against the dark-evasion threshold."""
    if not rows:
        return None
    fig, ax = plt.subplots(figsize=(7.0, 0.34 * len(rows) + 0.5))
    labels = [r["label"] for r in rows][::-1]
    vals = [r["cumulative"] for r in rows][::-1]
    ax.barh(range(len(vals)), [1.0] * len(vals), color=FAINT, height=0.55, zorder=1)
    ax.barh(range(len(vals)), vals, color=[ACCENT if i == 0 else NAVY for i in range(len(vals))], height=0.55, zorder=2)
    ax.axvline(threshold, color=ACCENT, lw=0.9, ls=(0, (3, 2)), zorder=3)
    ax.set_yticks(range(len(vals))); ax.set_yticklabels(labels, fontsize=7.2, color=INK)
    for i, r in enumerate(rows[::-1]):
        ax.text(1.015, i, f"{r['delta']:+.2f} = {r['cumulative']:.2f}" if r.get("delta") not in (None, 0) else f"{r['cumulative']:.2f}", va="center", fontsize=6.8, family="DejaVu Sans Mono", color=MUTED)
    ax.set_xlim(0, 1); ax.set_xticks([0, 0.4, 0.7, 1.0]); ax.grid(False); ax.grid(axis="x")
    ax.tick_params(axis="y", length=0)
    for s in ("left", "bottom"):
        ax.spines[s].set_visible(False)
    return _png(fig)


def sensitivity_curve(points: List[tuple], baseline: tuple) -> Optional[bytes]:
    if not points:
        return None
    xs, ys = zip(*points)
    fig, ax = plt.subplots(figsize=(3.4, 2.1))
    ax.plot(xs, ys, color=NAVY, lw=1.2)
    ax.axhline(0.70, color=ACCENT, lw=0.8, ls=(0, (3, 2))); ax.text(xs[-1], 0.625, "0.70 dark-evasion line", fontsize=6.2, color=ACCENT, ha="right")
    ax.axvline(30, color=MUTED, lw=0.6, ls=":"); ax.text(32, 0.04, "30 m", fontsize=6.2, color=MUTED)
    ax.scatter([baseline[0]], [baseline[1]], s=22, c=ACCENT, zorder=5, edgecolors="white", linewidths=0.6)
    ax.set_xlabel("Measured length (m)", fontsize=6.8); ax.set_ylabel("Dark-vessel probability", fontsize=6.8); ax.set_ylim(0, 1)
    return _png(fig)


def counterfactual_bars(rows: List[Dict[str, Any]]) -> Optional[bytes]:
    if not rows:
        return None
    fig, ax = plt.subplots(figsize=(3.6, 0.3 * len(rows) + 0.6))
    labels = [r["label"] for r in rows][::-1]
    vals = [r["probability"] for r in rows][::-1]
    ax.barh(labels, vals, color=[ACCENT if lab.startswith("Baseline") else NAVY for lab in labels], height=0.55)
    for i, v in enumerate(vals):
        ax.text(v + 0.015, i, f"{v:.2f}", va="center", fontsize=6.5, family="DejaVu Sans Mono", color=MUTED)
    ax.axvline(0.70, color=ACCENT, lw=0.8, ls=(0, (3, 2)))
    ax.set_xlim(0, 1.1); ax.grid(False); ax.grid(axis="x"); ax.tick_params(axis="y", length=0, labelsize=6.6)
    for s in ("left",):
        ax.spines[s].set_visible(False)
    return _png(fig)


_NODES = ["Mission", "SAR–AIS\ncorrelate", "Features", "Sanctions", "Forensic\nassess", "Human\nreview", "Report"]
_NODE_IDS = ["MissionController", "SARAISCorrelator", "FeatureEngineerNode", "SanctionsScreenerNode", "ForensicAssessorNode", "HumanReviewNode", "ReportPreparerNode"]


def workflow_diagram(trace: List[Dict[str, Any]]) -> bytes:
    status = {t["agent_name"]: t.get("status", "SUCCESS") for t in trace}
    fig, ax = plt.subplots(figsize=(7.0, 1.15))
    ax.set_xlim(0, 7.4); ax.set_ylim(0, 1.2); ax.axis("off"); ax.grid(False)
    for i, (label, nid) in enumerate(zip(_NODES, _NODE_IDS)):
        x = 0.05 + i * 1.05
        st = status.get(nid)
        fc = NAVY if st in ("SUCCESS", "APPROVED") else ("white" if st is None else "#FFFFFF")
        ec = ACCENT if st in ("DEGRADED", "FAILED", "OVERRIDDEN") else (NAVY if st else GRID)
        ax.add_patch(Rectangle((x, 0.3), 0.9, 0.7, fc=fc, ec=ec, lw=1.2 if st else 0.8, ls="-" if st else (0, (3, 2))))
        color = "white" if st in ("SUCCESS", "APPROVED") else (INK if st else MUTED)
        ax.text(x + 0.45, 0.65, label, ha="center", va="center", fontsize=6.4, color=color)
        ax.text(x + 0.03, 0.04, f"{i + 1:02d}" + ("" if st else " skipped"), fontsize=5.8, family="DejaVu Sans Mono", color=MUTED)
        if i < 6:
            ax.annotate("", xy=(x + 1.03, 0.65), xytext=(x + 0.92, 0.65), arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.7))
    return _png(fig)


def latency_chart(trace: List[Dict[str, Any]]) -> Optional[bytes]:
    rows = [(t["agent_name"], t.get("latency_ms", (t.get("details") or {}).get("latency_ms"))) for t in trace]
    rows = [(n, float(v)) for n, v in rows if v is not None]
    if not rows:
        return None
    fig, ax = plt.subplots(figsize=(3.6, 0.28 * len(rows) + 0.6))
    ax.barh([r[0].replace("Node", "") for r in rows][::-1], [r[1] for r in rows][::-1], color=NAVY, height=0.55)
    ax.set_xlabel("Wall-clock time (ms)", fontsize=6.8); ax.grid(False); ax.grid(axis="x"); ax.tick_params(axis="y", length=0, labelsize=6.6)
    ax.spines["left"].set_visible(False)
    return _png(fig)


def ais_gap_chart(gaps: List[Dict[str, Any]]) -> Optional[bytes]:
    if not gaps:
        return None
    fig, ax = plt.subplots(figsize=(3.6, 0.3 * len(gaps) + 1.0))
    ax.barh([f"Gap {i + 1}" for i in range(len(gaps))][::-1], [g["duration_hours"] for g in gaps][::-1],
            color=[ACCENT if g.get("is_suspicious") else "#B9C3CD" for g in gaps][::-1], height=0.4)
    ax.set_ylim(-0.7, len(gaps) - 0.3)
    ax.axvline(12, color=NAVY, lw=0.8, ls=(0, (3, 2))); ax.text(12.3, -0.45, "12 h trigger", fontsize=6.2, color=NAVY)
    ax.set_xlabel("Hours without a broadcast", fontsize=6.8); ax.grid(False); ax.grid(axis="x"); ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    return _png(fig)
