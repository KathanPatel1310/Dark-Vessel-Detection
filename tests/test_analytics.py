import unittest
from datetime import datetime, timezone
from src.schemas import SARDetection, SanctionsResult, SanctionMatch
from src.geospatial.eez_checker import RealEEZChecker
from src.features.pipeline import FeaturePipeline
from src.analytics.risk_scorer import MaritimeRiskScorer

class TestAnalytics(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.eez_checker = RealEEZChecker()
        
        # High-risk dark vessel in Arabian Sea evasion corridor
        self.sar_det = SARDetection(
            detection_id="SAR-RISK-001",
            scene_id="S1A_SCENE",
            timestamp=self.now,
            latitude=19.34,
            longitude=62.11,
            length_m=182.0, # Large commercial tanker
            width_m=28.0,
            aspect_ratio=6.5,
            heading_deg=247.0,
            confidence=0.92
        )

    def test_deliberate_dark_vessel_risk_scoring(self):
        geo_ctx = self.eez_checker.get_geo_context(self.sar_det.latitude, self.sar_det.longitude)
        features = FeaturePipeline.extract(
            sar_detection=self.sar_det,
            geo_context=geo_ctx,
            candidate_ais=None # Unmatched / dark
        )

        sanctions_match = SanctionMatch(
            source_list="OFAC_SDN",
            entity_name="SANCTIONED TANKER",
            entity_type="VESSEL",
            matched_imo="9187629",
            sanction_programs=["IRAN"],
            match_score=1.0,
            match_basis="EXACT_IMO_MATCH"
        )
        sanctions_res = SanctionsResult(
            query_target="9187629",
            is_sanctioned=True,
            overall_sanctions_risk="CONFIRMED",
            matches=[sanctions_match]
        )

        assessment = MaritimeRiskScorer.compute_risk_assessment(features, sanctions_res, geo_ctx)
        self.assertGreaterEqual(assessment.dark_vessel_probability, 0.70)
        self.assertEqual(assessment.dark_vessel_classification, "DELIBERATE_DARK_EVASION")
        self.assertEqual(assessment.sanctions_risk_level, "CRITICAL")
        self.assertGreater(assessment.overall_anomaly_score, 0.75)

    def test_small_craft_exemption(self):
        # Small dhow (length 18m) off coast
        small_sar = SARDetection(
            detection_id="SAR-SMALL",
            scene_id="S1A_SCENE",
            timestamp=self.now,
            latitude=20.8,
            longitude=70.4, # Near Gujarat coast
            length_m=18.0,
            width_m=5.0,
            aspect_ratio=3.6,
            confidence=0.85
        )
        geo_ctx = self.eez_checker.get_geo_context(small_sar.latitude, small_sar.longitude)
        features = FeaturePipeline.extract(sar_detection=small_sar, geo_context=geo_ctx, candidate_ais=None)
        clean_sanctions = SanctionsResult(query_target="NONE", is_sanctioned=False)

        assessment = MaritimeRiskScorer.compute_risk_assessment(features, clean_sanctions, geo_ctx)
        self.assertLess(assessment.dark_vessel_probability, 0.40)
        self.assertEqual(assessment.dark_vessel_classification, "SMALL_CRAFT_EXEMPT")

    def test_kinematic_trajectory_extrapolation(self):
        forecast = MaritimeRiskScorer.extrapolate_trajectory(
            lat=19.34,
            lon=62.11,
            speed_knots=10.0,
            heading_deg=247.0, # West-southwest
            start_time=self.now,
            forecast_horizons_hours=[6.0, 12.0, 24.0]
        )
        self.assertEqual(len(forecast.extrapolated_waypoints), 3)
        wp_6h, wp_12h, wp_24h = forecast.extrapolated_waypoints
        
        # Heading 247 deg should move latitude south (< 19.34) and longitude west (< 62.11)
        self.assertLess(wp_6h.projected_lat, 19.34)
        self.assertLess(wp_6h.projected_lon, 62.11)
        self.assertLess(wp_12h.projected_lat, wp_6h.projected_lat)
        self.assertLess(wp_24h.projected_lon, wp_12h.projected_lon)
        
        # Uncertainty cone should strictly expand with time
        self.assertLess(wp_6h.uncertainty_radius_km, wp_12h.uncertainty_radius_km)
        self.assertLess(wp_12h.uncertainty_radius_km, wp_24h.uncertainty_radius_km)

if __name__ == "__main__":
    unittest.main()
