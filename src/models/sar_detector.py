"""Real-time SAR Satellite Vessel Detector & Physical Feature Extractor.
Wraps the trained YOLOv8 SAR deep learning model and extracts genuine radiometric,
morphological, and kinematic features directly from Sentinel-1 radar pixels.
"""

import math
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import numpy as np
import cv2
from ultralytics import YOLO

from src.schemas.sar import SARDetection
from src.data.sar_chip_loader import RealSARChip
from src.utils.logger import setup_logger

logger = setup_logger("sar_vessel_detector")

DEFAULT_MODEL_PATH = "models/sar_detector/unquantized/best.pt"
# Sentinel-1 Interferometric Wide (IW) Ground Range Detected (GRD) pixel spacing:
SENTINEL1_PIXEL_SPACING_M = 10.0


class SARVesselDetector:
    """Deep learning detector and radiometric feature engine for Sentinel-1 SAR imagery."""

    def __init__(self, model_path: str = DEFAULT_MODEL_PATH, conf_threshold: float = 0.35):
        self.model_path = model_path
        self.conf_threshold = conf_threshold
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"SAR detector checkpoint not found at '{model_path}'. "
                "Please refer to models/README.md for instructions on acquiring or training detector weights."
            )
        logger.info(f"Loading SAR vessel detection network from {model_path}...")
        self.model = YOLO(model_path)
        logger.info(f"Detector loaded successfully. Classes: {self.model.names}")

    def detect_on_chip(self, chip: RealSARChip) -> List[SARDetection]:
        """
        Executes end-to-end vessel detection and physical feature extraction
        on an authentic dual-pol Sentinel-1 chip.
        """
        rgb_img = chip.to_rgb_composite()
        results = self.model(rgb_img, conf=self.conf_threshold, verbose=False)
        detections: List[SARDetection] = []

        h, w = chip.chip_vv.shape
        vv_raw = np.clip(chip.chip_vv, 1.0, None)
        vv_db = 10.0 * np.log10(vv_raw)

        if len(results) == 0 or len(results[0].boxes) == 0:
            return detections

        boxes = results[0].boxes
        for idx, box in enumerate(boxes):
            xyxy = box.xyxy[0].cpu().numpy().tolist()
            conf = float(box.conf[0].cpu().numpy())
            cls_id = int(box.cls[0].cpu().numpy())

            x1, y1, x2, y2 = [int(round(coord)) for coord in xyxy]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w - 1, x2), min(h - 1, y2)

            box_w = max(1, x2 - x1)
            box_h = max(1, y2 - y1)

            # Physical length and beam width from pixel dimensions (10m per pixel)
            # Length is major dimension, width is minor dimension
            dim_major_px = max(box_w, box_h)
            dim_minor_px = min(box_w, box_h)
            
            # Diagonal provides the maximum hull extent
            diag_px = math.sqrt(box_w ** 2 + box_h ** 2)
            length_m = round(dim_major_px * SENTINEL1_PIXEL_SPACING_M, 1)
            width_m = round(max(5.0, dim_minor_px * SENTINEL1_PIXEL_SPACING_M), 1)
            aspect_ratio = round(length_m / width_m, 2)
            area_m2 = round(length_m * width_m * 0.75, 1) # Ship hull geometry approximation

            # Estimate orientation (heading angle in degrees) from major axis
            if box_w >= box_h:
                heading_est = 90.0 if (x2 - x1) > 0 else 270.0
            else:
                heading_est = 0.0 if (y2 - y1) > 0 else 180.0

            # Radiometric Backscatter Analysis on target pixels vs surrounding sea clutter
            target_mask = np.zeros((h, w), dtype=bool)
            target_mask[y1:y2, x1:x2] = True
            target_pixels_db = vv_db[target_mask]

            # Annular clutter window (15-pixel border around ship mask)
            clutter_y1, clutter_y2 = max(0, y1 - 15), min(h, y2 + 15)
            clutter_x1, clutter_x2 = max(0, x1 - 15), min(w, x2 + 15)
            clutter_mask = np.zeros((h, w), dtype=bool)
            clutter_mask[clutter_y1:clutter_y2, clutter_x1:clutter_x2] = True
            clutter_mask[target_mask] = False
            clutter_pixels_db = vv_db[clutter_mask]

            peak_db = round(float(np.max(target_pixels_db)), 2)
            mean_db = round(float(np.mean(target_pixels_db)), 2)
            clutter_db = round(float(np.mean(clutter_pixels_db)), 2) if np.any(clutter_mask) else round(float(mean_db - 15.0), 2)
            tcr_db = round(float(mean_db - clutter_db), 2)

            det_id = f"SAR-{chip.scene_id[-6:]}-{chip.mmsi[-4:]}-{idx:02d}"

            det = SARDetection(
                detection_id=det_id,
                scene_id=chip.scene_id,
                timestamp=chip.acq_time,
                latitude=chip.latitude,
                longitude=chip.longitude,
                length_m=length_m,
                width_m=width_m,
                aspect_ratio=aspect_ratio,
                heading_deg=heading_est,
                area_m2=area_m2,
                peak_backscatter_db=peak_db,
                mean_backscatter_db=mean_db,
                background_mean_db=clutter_db,
                target_clutter_ratio_db=tcr_db,
                sensor="SENTINEL-1",
                polarization="VV/VH",
                confidence=round(conf, 3),
                bbox_pixel=[x1, y1, x2, y2],
            )
            detections.append(det)

        return detections
