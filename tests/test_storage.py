import unittest
import os
import tempfile
from src.utils.storage import StorageGuard

class TestStorageGuard(unittest.TestCase):
    def test_get_disk_free_gb(self):
        free_gb = StorageGuard.get_disk_free_gb(".")
        self.assertIsInstance(free_gb, float)
        self.assertGreater(free_gb, 0.0)

    def test_get_dir_size_mb(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "sample.txt")
            with open(test_file, "w") as f:
                f.write("A" * 1024 * 1024) # 1 MB
            size_mb = StorageGuard.get_dir_size_mb(tmpdir)
            self.assertTrue(0.95 <= size_mb <= 1.05)

    def test_estimate_download_safety(self):
        # A tiny download (e.g. 1 MB) should be approved
        is_safe, msg = StorageGuard.estimate_download_safety("Mock Tiny File", required_mb=1.0)
        self.assertTrue(is_safe)
        self.assertIn("APPROVED", msg)
        self.assertIn("Mock Tiny File", msg)

        # A giant download should be rejected
        is_safe, msg = StorageGuard.estimate_download_safety("Mock Giant Dataset", required_mb=500_000_000.0)
        self.assertFalse(is_safe)
        self.assertIn("REJECTED", msg)

if __name__ == "__main__":
    unittest.main()
