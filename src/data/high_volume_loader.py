"""Data Access Layer for High-Volume Real Datasets.
Provides high-performance streaming, filtering, and conversion from Parquet/CSV
into typed Pydantic objects for the Feature Engineering pipeline.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
import pandas as pd
from src.schemas.sar import SARDetection
from src.schemas.ais import AISObservation
from src.utils.logger import setup_logger

logger = setup_logger("high_volume_loader")

class HighVolumeDataLoader:
    """Streams and converts tabular SAR and AIS records into typed pipeline entities."""

    def __init__(
        self,
        sar_csv_path: str = "data/raw/sar/real_sar_detections.csv",
        ais_parquet_path: str = "data/raw/ais/real_ais_traffic.parquet"
    ):
        self.sar_csv_path = sar_csv_path
        self.ais_parquet_path = ais_parquet_path

    def get_summary_statistics(self) -> Dict[str, int]:
        """Returns row counts and metadata across all real tables."""
        sar_count = 0
        ais_count = 0
        dark_vessels = 0

        if pd.io.common.file_exists(self.sar_csv_path):
            df_sar = pd.read_csv(self.sar_csv_path)
            sar_count = len(df_sar)
            dark_vessels = len(df_sar[df_sar["matched_ais"] == False])

        if pd.io.common.file_exists(self.ais_parquet_path):
            df_ais = pd.read_parquet(self.ais_parquet_path)
            ais_count = len(df_ais)

        return {
            "total_sar_detections": sar_count,
            "dark_vessels_detected": dark_vessels,
            "matched_sar_vessels": sar_count - dark_vessels,
            "total_ais_trajectory_pings": ais_count
        }

    def load_sar_detections(self, limit: Optional[int] = None, only_dark: bool = False) -> List[SARDetection]:
        """Loads real Sentinel-1 SAR detections into SARDetection schema objects."""
        df = pd.read_csv(self.sar_csv_path)
        if only_dark:
            df = df[df["matched_ais"] == False]
        if limit:
            df = df.head(limit)

        detections = []
        for _, row in df.iterrows():
            ts = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
            detections.append(SARDetection(
                detection_id=row["detect_id"],
                scene_id=row["scene_id"],
                timestamp=ts,
                latitude=float(row["detect_lat"]),
                longitude=float(row["detect_lon"]),
                length_m=float(row["vessel_length_m"]),
                width_m=float(row["vessel_width_m"]),
                aspect_ratio=float(row["aspect_ratio"]),
                heading_deg=float(row["heading_deg"]),
                target_clutter_ratio_db=float(row["target_clutter_ratio_db"]),
                confidence=0.95 if row["confidence"] == "HIGH" else 0.80
            ))
        return detections

    def load_ais_observations(self, mmsi: Optional[str] = None, limit: Optional[int] = None) -> List[AISObservation]:
        """Loads real AIS trajectory pings into AISObservation schema objects."""
        df = pd.read_parquet(self.ais_parquet_path)
        if mmsi:
            df = df[df["MMSI"] == str(mmsi)]
        if limit:
            df = df.head(limit)

        observations = []
        for _, row in df.iterrows():
            ts = datetime.fromisoformat(row["BaseDateTime"].replace("Z", "+00:00"))
            observations.append(AISObservation(
                mmsi=str(row["MMSI"]),
                imo=str(row["IMO"]),
                vessel_name=row["VesselName"],
                callsign=row["CallSign"],
                ship_type="Tanker" if row["VesselType"] == 80 else "Cargo",
                latitude=float(row["LAT"]),
                longitude=float(row["LON"]),
                sog=float(row["SOG"]),
                cog=float(row["COG"]),
                heading=float(row["Heading"]),
                draught_m=float(row["Draft"]),
                timestamp=ts
            ))
        return observations
