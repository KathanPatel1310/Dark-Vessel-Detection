import os
from pathlib import Path
from typing import Any, Dict
import yaml

def get_project_root() -> Path:
    """Returns absolute path to the project root directory."""
    return Path(__file__).resolve().parent.parent.parent

def load_config(config_path: str = "configs/config.yaml") -> Dict[str, Any]:
    """Loads configuration from yaml file."""
    root = get_project_root()
    full_path = root / config_path
    if not full_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {full_path}")
    with open(full_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
