"""Generates explicit synthetic test fixtures for offline development and testing.
ALL DATA GENERATED HERE IS EXPLICITLY LABELED AS SYNTHETIC.
"""

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

def generate_synthetic_fixtures(output_dir: str = "data/fixtures") -> Dict[str, str]:
    """Creates synthetic SAR, AIS, Sanctions, and Registry test records."""
    os.makedirs(output_dir, exist_ok=True)
    base_time = datetime(2026, 9, 1, 3, 42, 0, tzinfo=timezone.utc)
    
    # 1. Synthetic SAR Detections (Arabian Sea)
    sar_detections = {
        "metadata": {
            "source": "SYNTHETIC_GENERATED",
            "description": "Simulated Sentinel-1 SAR detections in the Arabian Sea corridor",
            "scene_id": "S1A_IW_GRDH_1SDV_20260901T034200_SYNTHETIC",
            "generated_at": datetime.now(timezone.utc).isoformat()
        },
        "detections": [
            {
                "detection_id": "SAR-DET-2026-001",
                "scene_id": "S1A_IW_GRDH_1SDV_20260901T034200_SYNTHETIC",
                "timestamp": base_time.isoformat(),
                "latitude": 19.342,
                "longitude": 62.115,
                "length_m": 182.5,
                "width_m": 27.2,
                "aspect_ratio": 6.71,
                "heading_deg": 248.0,
                "area_m2": 4964.0,
                "peak_backscatter_db": 18.4,
                "mean_backscatter_db": 11.2,
                "background_mean_db": -16.5,
                "target_clutter_ratio_db": 27.7,
                "sensor": "SENTINEL-1",
                "polarization": "VV",
                "confidence": 0.94,
                "bbox_pixel": [420, 1150, 475, 1260]
            },
            {
                "detection_id": "SAR-DET-2026-002",
                "scene_id": "S1A_IW_GRDH_1SDV_20260901T034200_SYNTHETIC",
                "timestamp": base_time.isoformat(),
                "latitude": 20.105,
                "longitude": 63.420,
                "length_m": 85.0,
                "width_m": 14.0,
                "aspect_ratio": 6.07,
                "heading_deg": 110.0,
                "area_m2": 1190.0,
                "peak_backscatter_db": 14.1,
                "mean_backscatter_db": 8.5,
                "background_mean_db": -17.0,
                "target_clutter_ratio_db": 25.5,
                "sensor": "SENTINEL-1",
                "polarization": "VV",
                "confidence": 0.89,
                "bbox_pixel": [800, 2100, 840, 2180]
            }
        ]
    }
    sar_path = os.path.join(output_dir, "synthetic_sar_detections.json")
    with open(sar_path, "w", encoding="utf-8") as f:
        json.dump(sar_detections, f, indent=2)

    # 2. Synthetic AIS Observations and Transmission Gaps
    # Target 1 (Dark Tanker): last broadcast was 31 hours ago in Gulf of Oman
    # Target 2 (Normal Cargo): correlated AIS ping nearby
    ais_data = {
        "metadata": {
            "source": "SYNTHETIC_GENERATED",
            "description": "Simulated AIS feeds including regular broadcasts and deliberate outages",
            "generated_at": datetime.now(timezone.utc).isoformat()
        },
        "active_broadcasts": [
            {
                "mmsi": "412345678",
                "imo": "9345678",
                "vessel_name": "PACIFIC GLORY",
                "callsign": "VRAB2",
                "ship_type": "Cargo",
                "latitude": 20.108,
                "longitude": 63.424,
                "sog": 12.4,
                "cog": 112.0,
                "heading": 111.0,
                "draught_m": 9.2,
                "destination": "MUNDRA",
                "timestamp": base_time.isoformat(),
                "flag_country": "Liberia"
            }
        ],
        "historical_gaps": [
            {
                "mmsi": "352999001",
                "gap_start": (base_time - timedelta(hours=31)).isoformat(),
                "gap_end": None,
                "duration_hours": 31.0,
                "start_lat": 24.150,
                "start_lon": 58.200,
                "end_lat": None,
                "end_lon": None,
                "distance_covered_km": 680.0,
                "implied_speed_knots": 11.8,
                "is_suspicious": True,
                "justification": "AIS transponder disabled upon entering Arabian Sea sanctions evasion corridor."
            }
        ]
    }
    ais_path = os.path.join(output_dir, "synthetic_ais_tracks.json")
    with open(ais_path, "w", encoding="utf-8") as f:
        json.dump(ais_data, f, indent=2)

    # 3. Synthetic Sanctions Sample (OFAC / UN Format)
    sanctions_data = {
        "metadata": {
            "source": "SYNTHETIC_GENERATED",
            "description": "Simulated OFAC SDN and UN maritime sanctions watchlist sample",
            "generated_at": datetime.now(timezone.utc).isoformat()
        },
        "sanctioned_entities": [
            {
                "source_list": "OFAC_SDN",
                "entity_name": "STARLIGHT TRADER",
                "entity_type": "VESSEL",
                "matched_imo": "9284728",
                "matched_mmsi": "352999001",
                "matched_callsign": "H9ZT",
                "flag_state": "Panama",
                "sanction_programs": ["IRAN-EO13846"],
                "designation_date": "2024-03-15",
                "remarks": "Subject to secondary sanctions for illicit ship-to-ship petroleum transport."
            }
        ]
    }
    sanctions_path = os.path.join(output_dir, "synthetic_sanctions_sample.json")
    with open(sanctions_path, "w", encoding="utf-8") as f:
        json.dump(sanctions_data, f, indent=2)

    # 4. Synthetic Vessel Registry
    registry_data = {
        "metadata": {
            "source": "SYNTHETIC_GENERATED",
            "description": "Simulated ITU/IMO registry lookup database",
            "generated_at": datetime.now(timezone.utc).isoformat()
        },
        "vessels": [
            {
                "imo": "9284728",
                "mmsi": "352999001",
                "name": "STARLIGHT TRADER",
                "callsign": "H9ZT",
                "flag": "Panama",
                "vessel_type": "Crude Oil Tanker",
                "built_year": 2008,
                "length_overall_m": 183.0,
                "beam_m": 27.4,
                "gross_tonnage": 28500.0,
                "deadweight_tonnage": 46000.0,
                "owner_name": "Oceanic Zenith Shipping Ltd",
                "operator_name": "Al-Bahar Ship Management"
            },
            {
                "imo": "9345678",
                "mmsi": "412345678",
                "name": "PACIFIC GLORY",
                "callsign": "VRAB2",
                "flag": "Liberia",
                "vessel_type": "Container Ship",
                "built_year": 2015,
                "length_overall_m": 86.0,
                "beam_m": 14.2,
                "gross_tonnage": 4200.0,
                "deadweight_tonnage": 6100.0,
                "owner_name": "Glory Maritime Services Inc",
                "operator_name": "Global Feeder Line"
            }
        ]
    }
    registry_path = os.path.join(output_dir, "synthetic_vessel_registry.json")
    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(registry_data, f, indent=2)

    return {
        "sar": sar_path,
        "ais": ais_path,
        "sanctions": sanctions_path,
        "registry": registry_path
    }

if __name__ == "__main__":
    generated = generate_synthetic_fixtures()
    print("Generated synthetic test fixtures:")
    for k, v in generated.items():
        print(f"  {k}: {v} ({os.path.getsize(v)} bytes)")
