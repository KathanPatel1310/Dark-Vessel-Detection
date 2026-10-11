"""Tests for the real Sentinel-1 case library, chip imagery, and data inventory."""

import io

import numpy as np
import pytest
from fastapi.testclient import TestClient

from src.api.server import app
from src.data import real_cases

client = TestClient(app)

pytestmark = pytest.mark.skipif(
    not real_cases.list_cases(), reason="real Sentinel-1 chips are not present on this machine"
)


def test_real_case_index_lists_chips_with_ground_truth():
    r = client.get("/api/cases/real")
    assert r.status_code == 200
    body = r.json()
    assert body["provenance"] == "REAL"
    assert body["total"] == len(real_cases.list_cases())
    first = body["cases"][0]
    for key in ("chip_id", "mmsi", "vessel_name", "true_length_m", "latitude", "longitude", "acq_time"):
        assert key in first


def test_real_case_runs_detector_and_uses_real_acquisition_time():
    chip_id = real_cases.list_cases()[0]["chip_id"]
    r = client.get(f"/api/cases/real/{chip_id}")
    assert r.status_code == 200
    case = r.json()
    assert case["provenance"]["ais"] == "REAL"
    assert case["ais_observation"]["mmsi"] == case["ground_truth"]["mmsi"]
    # Regression: acquisition time used to fall back to "now" when the ISO string failed to parse.
    assert case["sar_detection"]["timestamp"].startswith("2024-")
    assert len(case["all_detections"]) >= 1


def test_withholding_ais_is_labelled_counterfactual():
    chip_id = real_cases.list_cases()[0]["chip_id"]
    case = client.get(f"/api/cases/real/{chip_id}", params={"withhold_ais": True}).json()
    assert case["ais_observation"] is None
    assert case["provenance"]["ais"] == "UNAVAILABLE"
    assert "counterfactual" in case["provenance"]["note"].lower()
    assert case["scenario_type"] == "REAL_CHIP_AIS_WITHHELD"


def test_chip_image_is_png_and_rejects_bad_ids():
    chip_id = real_cases.list_cases()[0]["chip_id"]
    r = client.get(f"/api/chips/{chip_id}/image", params={"band": "vv"})
    assert r.status_code == 200 and r.content[:8] == b"\x89PNG\r\n\x1a\n"
    assert client.get("/api/chips/..%2F..%2Fetc/image").status_code in (404, 422)
    assert client.get("/api/chips/does_not_exist/image").status_code == 404


def test_real_chip_outside_dataset_coverage_is_flagged_not_misjudged():
    chip_id = real_cases.list_cases()[0]["chip_id"]
    case = client.get(f"/api/cases/real/{chip_id}", params={"withhold_ais": True}).json()
    res = client.post("/api/investigate", json={
        "sar_detection": case["sar_detection"], "matched_ais": None, "chip_id": chip_id,
        "simulate_ais_offline": True,
    })
    assert res.status_code == 200
    body = res.json()
    assert body["geo_context"]["in_coverage"] is False
    assert any("outside" in n.lower() for n in body["degradation_notes"])
    # No "deep international waters" factor may be applied outside coverage.
    assert not any("deep international waters" in f for f in body["risk_assessment"]["risk_factors"])


def test_upload_detection_uses_real_detector_and_validates_input():
    chip_id = real_cases.list_cases()[0]["chip_id"]
    path = real_cases.chip_path(chip_id)
    with open(path, "rb") as fh:
        ok = client.post("/api/detect/sar", files={"chip_file": ("chip.npz", fh.read())})
    assert ok.status_code == 200
    assert ok.json()["source"] == "UPLOADED_CHIP" and len(ok.json()["all_detections"]) >= 1

    buf = io.BytesIO()
    np.savez(buf, nothing=np.zeros(3))
    bad = client.post("/api/detect/sar", files={"chip_file": ("bad.npz", buf.getvalue())})
    assert bad.status_code == 400


def test_inventory_tags_real_and_synthetic_correctly():
    inv = client.get("/api/data/inventory").json()
    by_id = {a["id"]: a for a in inv["assets"]}
    assert by_id["sar_chips"]["provenance"] == "REAL"
    assert by_id["sar_chips"]["count"] == len(real_cases.list_cases())
    if "synthetic_ais" in by_id:
        assert by_id["synthetic_ais"]["provenance"] == "SYNTHETIC"
    assert by_id["scenarios"]["provenance"] == "SYNTHETIC"
