import unittest
from src.data.sanctions_parser import RealSanctionsDatabase

class TestRealSanctions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = RealSanctionsDatabase()

    def test_database_loaded_real_vessels(self):
        # We know OFAC + UN contains over 1,500 real vessels
        self.assertGreater(self.db.total_vessels_indexed, 1500)
        self.assertGreater(len(self.db.by_imo), 1000)

    def test_known_sanctioned_vessel_by_imo(self):
        # Real Iranian sanctioned vessel: ARTAVIL (IMO 9187629)
        result = self.db.screen_vessel(imo="9187629")
        self.assertTrue(result.is_sanctioned)
        self.assertEqual(result.overall_sanctions_risk, "CONFIRMED")
        self.assertTrue(any("IRAN" in p for m in result.matches for p in m.sanction_programs))

    def test_known_sanctioned_vessel_by_mmsi(self):
        # Real MMSI for ARTAVIL: 572469210
        result = self.db.screen_vessel(mmsi="572469210")
        self.assertTrue(result.is_sanctioned)
        self.assertEqual(result.matches[0].entity_name, "ARTAVIL")

    def test_benign_vessel_lookup(self):
        # Fake IMO should come back clean
        result = self.db.screen_vessel(imo="9999999", vessel_name="BENIGN MERCHANT")
        self.assertFalse(result.is_sanctioned)
        self.assertEqual(result.overall_sanctions_risk, "CLEAN")
        self.assertEqual(len(result.matches), 0)

if __name__ == "__main__":
    unittest.main()
