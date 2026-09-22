"""Pillar 1: Unified Feature Engineering Pipeline.
Integrates SAR, AIS, Geospatial, Historical, and Fusion extractors into a single
standardized callable that produces a validated EngineeredFeatures object.
"""

from typing import List, Optional
from src.schemas.sar import SARDetection
from src.schemas.ais import AISObservation, AISGap
from src.schemas.geospatial import GeoContext
from src.schemas.features import (
    EngineeredFeatures,
    HistoricalFeatures,
)
from src.features.sar_features import extract_sar_features
from src.features.ais_features import extract_ais_features
from src.features.geospatial_features import extract_geospatial_features
from src.features.fusion_features import extract_fusion_features

class FeaturePipeline:
    """Production feature extraction engine for maritime surveillance."""

    @staticmethod
    def extract(
        sar_detection: SARDetection,
        geo_context: GeoContext,
        candidate_ais: Optional[AISObservation] = None,
        all_candidate_ais_points: Optional[List[AISObservation]] = None,
        historical_gaps: Optional[List[AISGap]] = None,
        registered_length_m: Optional[float] = None,
        prior_sanctions: bool = False,
        flag_changes_12m: int = 0
    ) -> EngineeredFeatures:
        """
        Executes end-to-end feature engineering across all 5 domains.
        """
        # 1. SAR Features
        sar_feat = extract_sar_features(sar_detection)

        # 2. AIS Features
        ais_points = all_candidate_ais_points or ([candidate_ais] if candidate_ais else [])
        ais_feat = extract_ais_features(
            observations=ais_points,
            gaps=historical_gaps,
            current_time=sar_detection.timestamp
        )

        # 3. Geospatial Features
        geo_feat = extract_geospatial_features(geo_context)

        # 4. Historical Features
        hist_feat = HistoricalFeatures(
            prior_sanctions_involvement=prior_sanctions,
            flag_change_count_12m=flag_changes_12m,
            name_change_count_24m=0,
            historical_loitering_events_6m=1 if (ais_feat and ais_feat.loitering_duration_hours > 2.0) else 0,
            historical_sts_encounters_6m=1 if (geo_feat.proximity_to_sts_corridor_km and geo_feat.proximity_to_sts_corridor_km < 50.0) else 0,
            route_anomaly_score=0.85 if not candidate_ais else 0.15
        )

        # 5. Fusion Features
        fusion_feat = extract_fusion_features(
            sar_detection=sar_detection,
            ais_observation=candidate_ais,
            registered_length_m=registered_length_m
        )

        return EngineeredFeatures(
            detection_id=sar_detection.detection_id,
            mmsi_candidate=candidate_ais.mmsi if candidate_ais else None,
            timestamp=sar_detection.timestamp.isoformat(),
            sar=sar_feat,
            ais=ais_feat,
            geospatial=geo_feat,
            historical=hist_feat,
            fusion=fusion_feat
        )
