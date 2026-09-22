import unittest
from src.data.high_volume_loader import HighVolumeDataLoader
from src.geospatial.eez_checker import RealEEZChecker
from src.data.sanctions_parser import RealSanctionsDatabase
from src.features.pipeline import FeaturePipeline
from src.analytics.risk_scorer import MaritimeRiskScorer

class TestHighVolumeData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loader = HighVolumeDataLoader()
        cls.eez_checker = RealEEZChecker()
        cls.sanctions_db = RealSanctionsDatabase()

    def test_dataset_summary_statistics(self):
        stats = self.loader.get_summary_statistics()
        self.assertEqual(stats["total_sar_detections"], 35000)
        self.assertEqual(stats["total_ais_trajectory_pings"], 103120)
        self.assertGreater(stats["dark_vessels_detected"], 2000)

    def test_load_real_sar_detections(self):
        detections = self.loader.load_sar_detections(limit=10, only_dark=True)
        self.assertEqual(len(detections), 10)
        for d in detections:
            self.assertGreater(d.length_m, 0.0)
            self.assertGreater(d.width_m, 0.0)
            self.assertIsNotNone(d.aspect_ratio)

    def test_load_real_ais_observations(self):
        observations = self.loader.load_ais_observations(limit=25)
        self.assertEqual(len(observations), 25)
        for obs in observations:
            self.assertTrue(len(obs.mmsi) >= 7)
            self.assertGreaterEqual(obs.sog, 0.0)

    def test_end_to_end_pipeline_on_real_data(self):
        # Pick the first real dark SAR detection
        dark_target = self.loader.load_sar_detections(limit=1, only_dark=True)[0]
        
        # 1. Geospatial classification
        geo_ctx = self.eez_checker.get_geo_context(dark_target.latitude, dark_target.longitude)
        self.assertIsNotNone(geo_ctx)

        # 2. Real Sanctions lookup
        sanctions_res = self.sanctions_db.screen_vessel(imo="9187629") # query sanctioned tanker

        # 3. Pillar 1 Feature Engineering on real target
        features = FeaturePipeline.extract(
            sar_detection=dark_target,
            geo_context=geo_ctx,
            candidate_ais=None
        )
        flat_feats = features.to_flat_dict()
        self.assertIn("sar_length_m", flat_feats)
        self.assertIn("sar_aspect_ratio", flat_feats)
        self.assertIn("geo_distance_to_shore_km", flat_feats)
        self.assertEqual(flat_feats["fusion_is_spatially_correlated"], 0.0)

        # 4. Analytics Risk Assessment
        risk = MaritimeRiskScorer.compute_risk_assessment(features, sanctions_res, geo_ctx)
        self.assertIsNotNone(risk)
        self.assertGreater(risk.overall_anomaly_score, 0.5)

if __name__ == "__main__":
    unittest.main()
