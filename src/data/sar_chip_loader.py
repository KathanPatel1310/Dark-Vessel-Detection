"""Real Sentinel-1 SAR Chip Loader & Ingestion Engine.
Downloads and indexes real Sentinel-1 SAR chips (dual-polarization VV + VH)
with authentic AIS co-registered metadata (MMSI, speed, heading, true length, coordinates).
"""

import os
import glob
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import cv2
from huggingface_hub import hf_hub_download, HfApi
from src.utils.logger import setup_logger

logger = setup_logger("sar_chip_loader")

REPO_ID = "mshaya/sar-ship-gulf"
DEFAULT_LOCAL_DIR = "data/raw/sar/chips"

class RealSARChip:
    """Represents a single co-registered Sentinel-1 SAR chip with ground truth AIS telemetry."""
    def __init__(
        self,
        chip_path: str,
        chip_vv: np.ndarray,
        chip_vh: np.ndarray,
        mmsi: str,
        vessel_name: str,
        vessel_type: str,
        true_length_m: float,
        latitude: float,
        longitude: float,
        sog_knots: float,
        heading_deg: float,
        scene_id: str,
        acq_time: datetime,
        pixel_col: int,
        pixel_row: int,
    ):
        self.chip_path = chip_path
        self.chip_vv = chip_vv
        self.chip_vh = chip_vh
        self.mmsi = str(mmsi).strip()
        self.vessel_name = str(vessel_name).strip()
        self.vessel_type = str(vessel_type).strip()
        self.true_length_m = float(true_length_m)
        self.latitude = float(latitude)
        self.longitude = float(longitude)
        self.sog_knots = float(sog_knots)
        self.heading_deg = float(heading_deg)
        self.scene_id = str(scene_id).strip()
        self.acq_time = acq_time
        self.pixel_col = int(pixel_col)
        self.pixel_row = int(pixel_row)

    def to_rgb_composite(self) -> np.ndarray:
        """
        Generates calibrated 3-channel Pauli/dual-pol RGB false-color representation
        suitable for vision neural networks (YOLOv8 / Faster-RCNN).
        Channel 0: VV (dB scaled & normalized)
        Channel 1: VH (dB scaled & normalized)
        Channel 2: VV - VH difference (polarization ratio, highlights metallic structures)
        """
        vv_db = 10.0 * np.log10(np.clip(self.chip_vv, 1.0, None))
        vh_db = 10.0 * np.log10(np.clip(self.chip_vh, 1.0, None))

        vv_norm = cv2.normalize(vv_db, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        vh_norm = cv2.normalize(vh_db, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        diff_norm = cv2.normalize(vv_db - vh_db, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)

        return np.stack([vv_norm, vh_norm, diff_norm], axis=-1)

    @classmethod
    def load(cls, file_path: str) -> "RealSARChip":
        """Loads a .npz chip archive from local disk."""
        data = np.load(file_path, allow_pickle=True)
        acq_raw = str(data["acq_time"])
        try:
            # Parse format like '20240811T001843'
            acq_dt = datetime.strptime(acq_raw, "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
        except Exception:
            acq_dt = datetime.now(timezone.utc)

        return cls(
            chip_path=file_path,
            chip_vv=data["chip_vv"],
            chip_vh=data["chip_vh"],
            mmsi=str(data["mmsi"]),
            vessel_name=str(data.get("vessel_name", "UNKNOWN")),
            vessel_type=str(data.get("vessel_type", "COMMERCIAL")),
            true_length_m=float(data.get("length_m", 100.0)),
            latitude=float(data["lat"]),
            longitude=float(data["lon"]),
            sog_knots=float(data.get("sog", 0.0)),
            heading_deg=float(data.get("heading", 0.0)),
            scene_id=str(data.get("scene_id", "S1A_IW_GRDH")),
            acq_time=acq_dt,
            pixel_col=int(data.get("pixel_col", 256)),
            pixel_row=int(data.get("pixel_row", 256)),
        )


class RealSARDatasetLoader:
    """Manages downloading, caching, and serving real Sentinel-1 SAR chips."""
    def __init__(self, local_dir: str = DEFAULT_LOCAL_DIR):
        self.local_dir = local_dir
        os.makedirs(self.local_dir, exist_ok=True)

    def download_sample_chips(self, count: int = 100, max_per_scene: int = 25) -> List[str]:
        """
        Downloads a diverse batch of real Sentinel-1 SAR chips from Hugging Face.
        Caches them locally under self.local_dir.
        """
        api = HfApi()
        logger.info(f"Listing available SAR chips from {REPO_ID}...")
        all_files = [f for f in api.list_repo_files(REPO_ID, repo_type="dataset") if f.endswith(".npz")]
        logger.info(f"Discovered {len(all_files)} total Sentinel-1 chips in remote repository.")

        selected_files: List[str] = []
        scene_counts: Dict[str, int] = {}

        for f in all_files:
            parts = f.split("/")
            scene_name = parts[1] if len(parts) > 2 else "default_scene"
            if scene_counts.get(scene_name, 0) < max_per_scene:
                selected_files.append(f)
                scene_counts[scene_name] = scene_counts.get(scene_name, 0) + 1
            if len(selected_files) >= count:
                break

        downloaded_paths: List[str] = []
        logger.info(f"Downloading {len(selected_files)} real Sentinel-1 chips into {self.local_dir}...")

        for idx, remote_path in enumerate(selected_files):
            fname = os.path.basename(remote_path)
            local_target = os.path.join(self.local_dir, fname)

            if os.path.exists(local_target):
                downloaded_paths.append(local_target)
                continue

            try:
                cached = hf_hub_download(
                    repo_id=REPO_ID,
                    filename=remote_path,
                    repo_type="dataset"
                )
                import shutil
                shutil.copy2(cached, local_target)
                downloaded_paths.append(local_target)
                if (idx + 1) % 25 == 0 or (idx + 1) == len(selected_files):
                    logger.info(f"Downloaded [{idx + 1}/{len(selected_files)}] chips...")
            except Exception as e:
                logger.warning(f"Failed to download {remote_path}: {e}")

        logger.info(f"Successfully cached {len(downloaded_paths)} real SAR chips locally.")
        return downloaded_paths

    def load_all_chips(self) -> List[RealSARChip]:
        """Loads all cached SAR chips from the local directory."""
        files = glob.glob(os.path.join(self.local_dir, "*.npz"))
        chips: List[RealSARChip] = []
        for f in sorted(files):
            try:
                chips.append(RealSARChip.load(f))
            except Exception as e:
                logger.warning(f"Error loading chip {f}: {e}")
        return chips
