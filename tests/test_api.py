"""Automated Integration Tests for Maritime Intelligence FastAPI Server."""

import pytest
from fastapi.testclient import TestClient
from src.api.server import app

client = TestClient(app)


def test_api_health():
    """Validates health check endpoint and production assets counter."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ONLINE"
    assert data["assets"]["sar_satellite_detections"] == 35000
    assert data["assets"]["commercial_ais_points"] == 103120
    assert "orchestration_framework" in data["assets"]


def test_api_scenarios():
    """Validates retrieval of 5 operational benchmark scenarios."""
    response = client.get("/api/scenarios")
    assert response.status_code == 200
    scenarios = response.json()
    assert len(scenarios) >= 5

    # Check key scenario types exist
    types = [s["scenario_type"] for s in scenarios]
    assert "DELIBERATE_DARK_EVASION" in types
    assert "SANCTIONED_VESSEL" in types
    assert "NORMAL_CORRELATED" in types
    assert "SMALL_CRAFT_EXEMPT" in types
    assert "DEGRADED_EVIDENCE" in types


def test_api_detect_sar():
    """Validates SAR radar target detection and TCR measurement."""
    response = client.post("/api/detect/sar", data={"preset_scenario_id": "SCN-DARK-001"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["detection"]["length_m"] == 245.0
    assert data["radiometrics"]["tcr_db"] > 0


def test_api_features_extract():
    """Validates 5-domain feature engineering extraction."""
    payload = {
        "sar_detection": {
            "detection_id": "TEST-SAR-001",
            "scene_id": "SCENE-01",
            "timestamp": "2026-09-20T12:00:00Z",
            "latitude": 21.38,
            "longitude": 64.18,
            "length_m": 240.0,
            "width_m": 41.0,
            "aspect_ratio": 5.85,
            "heading_deg": 240.0,
            "confidence": 0.94
        },
        "candidate_ais": None,
        "historical_gaps": [],
        "prior_sanctions": False
    }
    response = client.post("/api/features/extract", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert "features" in data
    assert "flat_vector" in data
    assert len(data["flat_vector"]) >= 20
    assert data["flat_vector"]["sar_length_m"] == 240.0


def test_api_sanctions_screen():
    """Validates sub-millisecond screening against OFAC/UN indices."""
    # Test screening query
    payload = {
        "imo": "9187629",
        "vessel_name": "ARTAVIL",
        "force_offline": False
    }
    response = client.post("/api/sanctions/screen", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert "result" in data


def test_api_investigate_dark_vessel():
    """Validates end-to-end multi-agent LangGraph investigation pipeline."""
    payload = {
        "sar_detection": {
            "detection_id": "SAR-DET-2026-DARK-01",
            "scene_id": "S1A_ARABIAN_SEA",
            "timestamp": "2026-09-20T12:00:00Z",
            "latitude": 21.38,
            "longitude": 64.18,
            "length_m": 245.0,
            "width_m": 42.0,
            "aspect_ratio": 5.83,
            "heading_deg": 240.0,
            "confidence": 0.94
        },
        "matched_ais": None,
        "historical_gaps": [],
        "simulate_ais_offline": False,
        "simulate_sanctions_offline": False
    }
    response = client.post("/api/investigate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert len(data["execution_trace"]) >= 5
    assert data["human_in_the_loop_required"] is True
    assert data["risk_assessment"]["dark_vessel_classification"] == "DELIBERATE_DARK_EVASION"
    assert len(data["forecast"]["extrapolated_waypoints"]) == 3
    assert data["final_report"]["threat_tier"] in ["MEDIUM", "HIGH", "SEVERE"]


def test_api_hitl_submit():
    """Validates Human-in-the-Loop review disposition checkpoint."""
    # Run an investigation first to establish session
    inv_payload = {
        "sar_detection": {
            "detection_id": "SAR-DET-HITL-01",
            "scene_id": "S1A_ARABIAN_SEA",
            "timestamp": "2026-09-20T12:00:00Z",
            "latitude": 21.38,
            "longitude": 64.18,
            "length_m": 245.0,
            "width_m": 42.0,
            "aspect_ratio": 5.83,
            "heading_deg": 240.0,
            "confidence": 0.94
        }
    }
    inv_res = client.post("/api/investigate", json=inv_payload)
    session_id = inv_res.json()["session_id"]

    # Submit operator disposition
    hitl_payload = {
        "session_id": session_id,
        "analyst_disposition": "APPROVED",
        "audit_notes": "Target confirmed high-priority dark crude carrier. Coast Guard Sector 4 alerted for aerial reconnaissance."
    }
    hitl_res = client.post("/api/hitl/submit", json=hitl_payload)
    assert hitl_res.status_code == 200
    res_data = hitl_res.json()
    assert res_data["status"] == "SUCCESS"
    assert res_data["disposition"] == "APPROVED"
    assert "audit_trace" in res_data
