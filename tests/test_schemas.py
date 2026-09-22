import unittest
from datetime import datetime, timezone
from pydantic import ValidationError

from src.schemas import (
    Mission,
    BoundingBox,
    SARDetection,
    SARScene,
    AISObservation,
    AISGap,
    VesselIdentity,
    VesselCandidate,
    GeoContext,
    SanctionMatch,
    SanctionsResult,
    SARFeatures,
    AISFeatures,
    GeospatialFeatures,
    HistoricalFeatures,
    FusionFeatures,
    EngineeredFeatures,
    TrajectoryPoint,
    PredictiveForecast,
    RiskAssessment,
    IntelligenceReport,
    MaritimeAgentState,
)

class TestSchemas(unittest.TestCase):
    def test_mission_schema(self):
        bbox = BoundingBox(min_lat=12.0, max_lat=24.0, min_lon=58.0, max_lon=74.0)
        now = datetime.now(timezone.utc)
        mission = Mission(
            mission_id="MSN-2026-001",
            time_window_start=now,
            time_window_end=now,
            bbox=bbox,
        )
        self.assertEqual(mission.mission_id, "MSN-2026-001")
        self.assertEqual(mission.priority, "MEDIUM")

    def test_sar_detection_validation(self):
        now = datetime.now(timezone.utc)
        det = SARDetection(
            detection_id="DET-001",
            scene_id="S1A_IW_GRDH_1SDV_20260901_0342",
            timestamp=now,
            latitude=19.3,
            longitude=62.1,
            length_m=180.0,
            width_m=28.0,
            aspect_ratio=180.0 / 28.0,
            confidence=0.92,
        )
        self.assertEqual(det.length_m, 180.0)
        self.assertGreater(det.aspect_ratio, 6.0)

        with self.assertRaises(ValidationError):
            SARDetection(
                detection_id="DET-ERR",
                scene_id="S1A",
                timestamp=now,
                latitude=120.0, # invalid > 90
                longitude=62.1,
                length_m=100.0,
                width_m=20.0,
                aspect_ratio=5.0,
                confidence=0.8,
            )

    def test_engineered_features_flattening(self):
        sar_f = SARFeatures(
            length_m=175.0,
            width_m=26.0,
            aspect_ratio=175.0 / 26.0,
            detection_area_m2=4550.0,
            target_to_clutter_ratio_db=14.5,
        )
        ais_f = AISFeatures(
            mean_speed_knots=11.2,
            speed_variance=0.8,
            max_speed_knots=12.5,
            heading_variance=4.2,
            total_distance_km=340.0,
            current_gap_duration_hours=31.5,
        )
        geo_f = GeospatialFeatures(
            distance_to_shore_km=210.0,
            distance_to_nearest_port_km=280.0,
            distance_to_eez_boundary_km=45.0,
            is_inside_eez=False,
            is_inside_mpa_or_rfmo=False,
        )
        hist_f = HistoricalFeatures(
            prior_sanctions_involvement=True,
            flag_change_count_12m=2,
        )
        fusion_f = FusionFeatures(
            spatial_discrepancy_km=42.0,
            temporal_difference_minutes=1890.0,
            is_spatially_correlated=False,
            candidate_identity_score=0.25,
        )

        features = EngineeredFeatures(
            detection_id="DET-001",
            timestamp="2026-09-01T03:42:00Z",
            sar=sar_f,
            ais=ais_f,
            geospatial=geo_f,
            historical=hist_f,
            fusion=fusion_f,
        )

        flat = features.to_flat_dict()
        self.assertIsInstance(flat, dict)
        self.assertEqual(flat["sar_length_m"], 175.0)
        self.assertEqual(flat["ais_current_gap_duration_hours"], 31.5)
        self.assertEqual(flat["geo_is_inside_eez"], 0.0)
        self.assertEqual(flat["hist_prior_sanctions_involvement"], 1.0)
        self.assertEqual(flat["fusion_is_spatially_correlated"], 0.0)

    def test_agent_state_initialization(self):
        bbox = BoundingBox(min_lat=15.0, max_lat=22.0, min_lon=60.0, max_lon=70.0)
        now = datetime.now(timezone.utc)
        mission = Mission(
            mission_id="MSN-TEST",
            time_window_start=now,
            time_window_end=now,
            bbox=bbox,
        )
        state = MaritimeAgentState(mission=mission)
        self.assertEqual(state.current_node, "controller")
        self.assertEqual(len(state.degradation_notes), 0)
        self.assertIsNone(state.active_detection)

if __name__ == "__main__":
    unittest.main()
