"""Storage safety and estimation utility.
Enforces the strict requirement: ALWAYS assess and report storage requirements
before initiating external downloads or heavy processing.
"""

import os
import shutil
from typing import Dict, Tuple

class StorageGuard:
    """Manages disk space verification and storage budget adherence."""

    @staticmethod
    def get_disk_free_gb(path: str = ".") -> float:
        """Returns available free disk space in Gigabytes for the given path."""
        stat = shutil.disk_usage(os.path.abspath(path))
        return stat.free / (1024 ** 3)

    @staticmethod
    def get_dir_size_mb(path: str) -> float:
        """Returns total size of a directory in Megabytes."""
        if not os.path.exists(path):
            return 0.0
        total_bytes = 0
        for dirpath, _, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    total_bytes += os.path.getsize(fp)
        return total_bytes / (1024 ** 2)

    @classmethod
    def estimate_download_safety(
        cls,
        item_name: str,
        required_mb: float,
        target_dir: str = ".",
        safety_margin_ratio: float = 1.5
    ) -> Tuple[bool, str]:
        """
        Validates if downloading the item is safe given current free disk space.
        
        Returns:
            (is_safe, message_summary)
        """
        free_gb = cls.get_disk_free_gb(target_dir)
        required_gb = required_mb / 1024.0
        safe_threshold_gb = required_gb * safety_margin_ratio

        summary = (
            f"Storage Check for '{item_name}':\n"
            f"  - Required Space   : {required_mb:.1f} MB ({required_gb:.2f} GB)\n"
            f"  - Recommended Headroom: {safe_threshold_gb:.2f} GB\n"
            f"  - Available Disk Space: {free_gb:.2f} GB\n"
        )

        if free_gb < safe_threshold_gb:
            return False, summary + "  => STATUS: REJECTED (Insufficient disk headroom)."
        return True, summary + "  => STATUS: APPROVED (Sufficient disk headroom)."
