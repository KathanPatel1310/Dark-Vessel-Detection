import unittest
from datetime import datetime, timezone
from src.schemas import SARDetection, AISObservation, AISGap
from src.geospatial.eez_checker import RealEEZChecker
from src.features.sar_features import extract_sar_features, compute_aspect_ratio, compute_eccentricity
from src.features.ais_features import extract_ais_features, compute_circular_heading_variance
from src.features.fusion_features import extract_fusion_features
from src.features.pipeline import FeaturePipeline

class TestFeatures(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.sar_det = SARDetection(
            detection_id="SAR-TEST-001",
            scene_id="S1A_SCENE_TEST",
            timestamp=self.now,
            latitude=19.34,
            longitude=62.11,
            length_m=180.0,
            width_m=28.0,
            aspect_ratio=180.0 / 28.0,
            heading_deg=247.0,
            area_m2=4900.0,
            peak_backscatter_db=18.0,
            mean_backscatter_db=11.0,
            background_mean_db=-16.0,
            target_clutter_ratio_db=27.0,
            confidence=0.94
        )

    def test_sar_features(self):
        feat = extract_sar_features(self.sar_det)
        self.assertEqual(feat.length_m, 180.0)
        self.assertAlmostEqual(feat.aspect_ratio, 6.429, places=2)
        self.assertEqual(feat.target_to_clutter_ratio_db, 27.0)
        self.assertGreater(feat.eccentricity, 0.9) # High eccentricity for ship

    def test_ais_features(self):
        obs1 = AISObservation(
            mmsi="412345678", latitude=19.0, longitude=62.0, sog=12.0, cog=245.0, timestamp=self.now
        )
        obs2 = AISObservation(
            mmsi="412345678", latitude=19.1, longitude=62.2, sog=12.4, cog=247.0, timestamp=self.now
        )
        feat = extract_ais_features([obs1, obs2])
        self.assertAlmostEqual(feat.mean_speed_knots, 12.2, places=1)
        self.assertGreater(feat.total_distance_km, 0.0)
        self.assertLess(feat.heading_variance, 0.1) # Straight line

    def test_fusion_unmatched(self):
        # When target is completely dark
        fusion = extract_fusion_features(self.sar_det, ais_observation=None)
        self.assertFalse(fusion.is_spatially_correlated)
        self.assertEqual(fusion.candidate_identity_score, 0.0)
        self.assertEqual(fusion.spatial_discrepancy_km, 999.0)

    def test_fusion_matched(self):
        nearby_ais = AISObservation(
            mmsi="412345678",
            latitude=19.35, # ~1.5 km away
            longitude=62.12,
            sog=10.0,
            cog=248.0,
            timestamp=self.now
        )
        fusion = extract_fusion_features(self.sar_det, ais_observation=nearby_ais, registered_length_m=182.0)
        self.assertTrue(fusion.is_spatially_correlated)
        self.assertLess(fusion.spatial_discrepancy_km, 3.0)
        self.assertGreater(fusion.candidate_identity_score, 0.8)

    def test_feature_pipeline_flattening(self):
        eez_checker = RealEEZChecker()
        geo_ctx = eez_checker.get_geo_context(self.sar_det.latitude, self.sar_det.longitude)
        
        features = FeaturePipeline.extract(
            sar_detection=self.sar_det,
            geo_context=geo_ctx,
            candidate_ais=None
        )
        flat = features.to_flat_dict()
        self.assertIsInstance(flat, dict)
        self.assertEqual(flat["sar_length_m"], 180.0)
        self.assertEqual(flat["fusion_is_spatially_correlated"], 0.0)
        self.assertIn("geo_distance_to_shore_km", flat)

if __name__ == "__main__":
    unittest.main()
