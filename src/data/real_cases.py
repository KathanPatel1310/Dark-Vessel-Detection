"""Real Sentinel-1 case library.

Indexes the dual-pol SAR chips under ``data/raw/sar/chips`` (real imagery with
co-registered real AIS ground truth), runs the YOLO detector on demand, and turns a
chip into an investigation-ready case. Nothing here fabricates data: when AIS is
withheld the case is explicitly labelled as a counterfactual.
"""

import glob
import hashlib
import io
import math
import os
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from src.data.sar_chip_loader import DEFAULT_LOCAL_DIR, RealSARChip
from src.models.sar_detector import SARVesselDetector
from src.schemas.ais import AISObservation
from src.schemas.sar import SARDetection
from src.utils.logger import setup_logger

logger = setup_logger("real_cases")

DATASET_SOURCE = "Hugging Face mshaya/sar-ship-gulf (Sentinel-1 IW GRDH dual-pol chips with co-registered AIS)"
_AIS_TYPE_NAMES = {30: "Fishing", 35: "Military", 36: "Sailing", 37: "Pleasure craft", 60: "Passenger", 70: "Cargo", 80: "Tanker", 90: "Other"}

_lock = threading.Lock()
_detector: Optional[SARVesselDetector] = None
_index: Optional[List[Dict[str, Any]]] = None
_detection_cache: Dict[str, Tuple[RealSARChip, List[SARDetection]]] = {}


def _get_detector() -> SARVesselDetector:
    global _detector
    with _lock:
        if _detector is None:
            _detector = SARVesselDetector()
        return _detector


def ship_type_name(code: Any) -> str:
    try:
        c = int(code)
    except (TypeError, ValueError):
        return str(code)
    base = (c // 10) * 10
    return _AIS_TYPE_NAMES.get(c) or _AIS_TYPE_NAMES.get(base) or f"AIS type {c}"


def chip_path(chip_id: str, chip_dir: str = DEFAULT_LOCAL_DIR) -> str:
    if not chip_id or any(ch in chip_id for ch in ("/", "\\", ".")):
        raise FileNotFoundError(f"Invalid chip id {chip_id!r}")
    path = os.path.join(chip_dir, f"{chip_id}.npz")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Chip {chip_id} not found")
    return path


def list_cases(chip_dir: str = DEFAULT_LOCAL_DIR, refresh: bool = False) -> List[Dict[str, Any]]:
    """Lightweight metadata for every chip (scalars only; image arrays are not read)."""
    global _index
    with _lock:
        if _index is not None and not refresh:
            return _index
    rows: List[Dict[str, Any]] = []
    for f in sorted(glob.glob(os.path.join(chip_dir, "*.npz"))):
        try:
            with np.load(f, allow_pickle=False) as d:
                rows.append({
                    "chip_id": os.path.splitext(os.path.basename(f))[0],
                    "mmsi": str(int(d["mmsi"])),
                    "vessel_name": str(d["vessel_name"]),
                    "vessel_type": ship_type_name(d["vessel_type"]),
                    "true_length_m": float(d["length_m"]),
                    "latitude": float(d["lat"]),
                    "longitude": float(d["lon"]),
                    "sog_knots": float(d["sog"]),
                    "heading_deg": float(d["heading"]),
                    "acq_time": str(d["acq_time"]),
                    "scene_id": str(d["scene_id"]),
                    "n_other_ships": int(d["n_other_ships"]) if "n_other_ships" in d.files else None,
                    "size_bytes": os.path.getsize(f),
                })
        except Exception as e:  # a corrupt chip must not take the library down
            logger.warning(f"Skipping unreadable chip {f}: {e}")
    with _lock:
        _index = rows
    return rows


def _detect(chip_id: str, conf: float = 0.35) -> Tuple[RealSARChip, List[SARDetection]]:
    key = f"{chip_id}@{conf:.2f}"
    with _lock:
        if key in _detection_cache:
            return _detection_cache[key]
    chip = RealSARChip.load(chip_path(chip_id))
    det = _get_detector()
    with _lock:
        old = det.conf_threshold
        det.conf_threshold = conf
        try:
            dets = det.detect_on_chip(chip)
        finally:
            det.conf_threshold = old
        _detection_cache[key] = (chip, dets)
    return chip, dets


def primary_detection(dets: List[SARDetection], shape: Tuple[int, int]) -> Optional[SARDetection]:
    """The detection closest to the chip centre — chips are centred on the AIS-labelled ship."""
    if not dets:
        return None
    cy, cx = shape[0] / 2.0, shape[1] / 2.0

    def dist(d: SARDetection) -> float:
        x1, y1, x2, y2 = d.bbox_pixel or [0, 0, 0, 0]
        return math.hypot((x1 + x2) / 2.0 - cx, (y1 + y2) / 2.0 - cy)

    return min(dets, key=dist)


def _dt_sec(chip_id: str) -> float:
    try:
        with np.load(chip_path(chip_id), allow_pickle=False) as d:
            return float(d["dt_sec"]) if "dt_sec" in d.files else 0.0
    except Exception:
        return 0.0


def build_case(chip_id: str, withhold_ais: bool = False, conf: float = 0.35) -> Dict[str, Any]:
    chip, dets = _detect(chip_id, conf)
    primary = primary_detection(dets, chip.chip_vv.shape)
    if primary is None:
        raise LookupError(f"Detector found no vessel in chip {chip_id} at confidence {conf}")

    ais = AISObservation(
        mmsi=chip.mmsi,
        vessel_name=chip.vessel_name,
        ship_type=ship_type_name(chip.vessel_type),
        latitude=chip.latitude,
        longitude=chip.longitude,
        sog=min(max(chip.sog_knots, 0.0), 100.0),
        cog=chip.heading_deg % 360.0,
        heading=chip.heading_deg % 360.0,
        timestamp=chip.acq_time - timedelta(seconds=_dt_sec(chip_id)),
    )
    label = "AIS withheld (counterfactual)" if withhold_ais else "AIS co-registered"
    note = "Imagery and AIS are real; measurements are derived by the detector."
    if withhold_ais:
        note += " AIS was deliberately withheld to simulate a dark vessel: this is a counterfactual test, not an observed evasion."
    return {
        "scenario_id": f"REAL-{chip_id}",
        "scenario_name": f"{chip.vessel_name or 'Unnamed vessel'} — real Sentinel-1 chip",
        "scenario_type": "REAL_CHIP_AIS_WITHHELD" if withhold_ais else "REAL_CHIP",
        "description": (
            f"Real Sentinel-1 radar chip acquired {chip.acq_time:%Y-%m-%d %H:%M} UTC at "
            f"({chip.latitude:.3f}, {chip.longitude:.3f}). Ground-truth vessel: {chip.vessel_name} "
            f"(MMSI {chip.mmsi}, {chip.true_length_m:.0f} m). {label}."
        ),
        "expected_threat_tier": "—",
        "expected_classification": "—",
        "chip_id": chip_id,
        "sar_detection": primary.model_dump(mode="json"),
        "all_detections": [d.model_dump(mode="json") for d in dets],
        "ais_observation": None if withhold_ais else ais.model_dump(mode="json"),
        "ground_truth_ais": ais.model_dump(mode="json"),
        "historical_gaps": [],
        "ground_truth": {"mmsi": chip.mmsi, "vessel_name": chip.vessel_name, "length_m": chip.true_length_m},
        "provenance": {
            "radar": "DERIVED",
            "ais": "UNAVAILABLE" if withhold_ais else "REAL",
            "classification": "HEURISTIC",
            "imagery": "REAL",
            "source": DATASET_SOURCE,
            "note": note,
        },
    }


def render_chip_png(chip_id: str, band: str = "vv", boxes: bool = True, conf: float = 0.35) -> bytes:
    """dB-stretched (2-98 percentile) greyscale or false-colour PNG, optionally with detector boxes."""
    chip, dets = _detect(chip_id, conf)

    def stretch(a: np.ndarray) -> np.ndarray:
        db = 10.0 * np.log10(np.clip(a, 1.0, None))
        lo, hi = np.percentile(db, [2, 98])
        return np.clip((db - lo) / max(hi - lo, 1e-6) * 255.0, 0, 255).astype(np.uint8)

    if band == "vh":
        img = cv2.cvtColor(stretch(chip.chip_vh), cv2.COLOR_GRAY2BGR)
    elif band == "rgb":
        img = cv2.cvtColor(chip.to_rgb_composite(), cv2.COLOR_RGB2BGR)
    else:
        img = cv2.cvtColor(stretch(chip.chip_vv), cv2.COLOR_GRAY2BGR)

    if boxes:
        prim = primary_detection(dets, chip.chip_vv.shape)
        for d in dets:
            x1, y1, x2, y2 = d.bbox_pixel or [0, 0, 0, 0]
            is_p = prim is not None and d.detection_id == prim.detection_id
            color = (255, 229, 0) if is_p else (11, 158, 245)  # BGR: cyan target, amber others
            cv2.rectangle(img, (x1 - 3, y1 - 3), (x2 + 3, y2 + 3), color, 1)
            if is_p:
                cv2.rectangle(img, (x1 - 18, y1 - 18), (x2 + 18, y2 + 18), (20, 160, 245), 1, cv2.LINE_AA)  # clutter guard
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise RuntimeError("PNG encoding failed")
    return buf.tobytes()


def chip_from_npz_bytes(data: bytes, name: str = "upload") -> RealSARChip:
    """Builds a chip from an uploaded .npz (requires chip_vv + chip_vh; metadata optional)."""
    with np.load(io.BytesIO(data), allow_pickle=False) as d:
        if "chip_vv" not in d.files or "chip_vh" not in d.files:
            raise ValueError("npz must contain 'chip_vv' and 'chip_vh' arrays")
        vv, vh = d["chip_vv"].astype(np.float32), d["chip_vh"].astype(np.float32)
        if vv.ndim != 2 or vv.shape != vh.shape or max(vv.shape) > 2048:
            raise ValueError("chip_vv/chip_vh must be equal 2-D arrays up to 2048x2048")

        def g(key: str, default: Any) -> Any:
            return d[key].item() if key in d.files else default

        return RealSARChip(
            chip_path=name, chip_vv=vv, chip_vh=vh,
            mmsi=str(g("mmsi", "UNKNOWN")), vessel_name=str(g("vessel_name", "UNKNOWN")), vessel_type=str(g("vessel_type", "")),
            true_length_m=float(g("length_m", 0.0)), latitude=float(g("lat", 0.0)), longitude=float(g("lon", 0.0)),
            sog_knots=float(g("sog", 0.0)), heading_deg=float(g("heading", 0.0)), scene_id=str(g("scene_id", "UPLOADED_CHIP")),
            acq_time=datetime.now(timezone.utc), pixel_col=0, pixel_row=0,
        )


def detect_uploaded(data: bytes, name: str, conf: float) -> Tuple[RealSARChip, List[SARDetection]]:
    chip = chip_from_npz_bytes(data, name)
    det = _get_detector()
    with _lock:
        old = det.conf_threshold
        det.conf_threshold = conf
        try:
            return chip, det.detect_on_chip(chip)
        finally:
            det.conf_threshold = old


def sha256_file(path: str, max_bytes: int = 200 * 1024 * 1024) -> Optional[str]:
    if os.path.getsize(path) > max_bytes:
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()
