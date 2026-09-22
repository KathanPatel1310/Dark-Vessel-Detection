import json
import os
import unittest
from src.schemas import SARDetection, AISObservation, AISGap, SanctionMatch, VesselIdentity

class TestFixtures(unittest.TestCase):
    def test_load_synthetic_sar_fixtures(self):
        filepath = "data/fixtures/synthetic_sar_detections.json"
        self.assertTrue(os.path.exists(filepath))
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["metadata"]["source"], "SYNTHETIC_GENERATED")
        detections = [SARDetection(**d) for d in data["detections"]]
        self.assertEqual(len(detections), 2)
        self.assertEqual(detections[0].detection_id, "SAR-DET-2026-001")

    def test_load_synthetic_ais_fixtures(self):
        filepath = "data/fixtures/synthetic_ais_tracks.json"
        self.assertTrue(os.path.exists(filepath))
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        broadcasts = [AISObservation(**b) for b in data["active_broadcasts"]]
        gaps = [AISGap(**g) for g in data["historical_gaps"]]
        self.assertEqual(len(broadcasts), 1)
        self.assertEqual(len(gaps), 1)
        self.assertTrue(gaps[0].is_suspicious)

    def test_load_synthetic_sanctions_fixtures(self):
        filepath = "data/fixtures/synthetic_sanctions_sample.json"
        self.assertTrue(os.path.exists(filepath))
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        matches = [
            SanctionMatch(match_score=1.0, match_basis="EXACT_IMO", **item)
            for item in data["sanctioned_entities"]
        ]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].matched_imo, "9284728")

if __name__ == "__main__":
    unittest.main()
