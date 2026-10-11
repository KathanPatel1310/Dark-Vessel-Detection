"""Self-Check Automated Suite: Validates all 5 operational benchmark scenarios.

Asserts each scenario fixture loaded from data/fixtures/scenarios/*.json
executes cleanly through the multi-agent pipeline and yields its expected classification.
"""

import glob
import json
import os
import pytest
from fastapi.testclient import TestClient
from src.api.server import app

client = TestClient(app)

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "fixtures", "scenarios")


def load_all_scenario_fixtures():
    files = sorted(glob.glob(os.path.join(FIXTURES_DIR, "*.json")))
    assert len(files) >= 5, f"Expected at least 5 scenario fixtures in {FIXTURES_DIR}, found {len(files)}"
    scenarios = []
    for fpath in files:
        with open(fpath, "r", encoding="utf-8") as f:
            scenarios.append(json.load(f))
    return scenarios


@pytest.mark.parametrize("scenario", load_all_scenario_fixtures(), ids=lambda s: s["scenario_id"])
def test_scenario_execution(scenario):
    """Executes each scenario fixture through the real pipeline and asserts expected outcome."""
    payload = {
        "mission_id": f"TEST-{scenario['scenario_id']}",
        "sar_detection": scenario["sar_detection"],
        "matched_ais": scenario.get("ais_observation"),
        "historical_gaps": scenario.get("historical_gaps") or [],
        "simulate_ais_offline": scenario.get("scenario_type") == "DEGRADED_EVIDENCE",
        "simulate_sanctions_offline": scenario.get("scenario_type") == "DEGRADED_EVIDENCE",
    }

    response = client.post("/api/investigate", json=payload)
    assert response.status_code == 200, f"Investigation failed for {scenario['scenario_id']}: {response.text}"

    data = response.json()
    assert data["status"] == "SUCCESS"
    assert "execution_trace" in data
    assert len(data["execution_trace"]) >= 5

    # Check risk classification
    risk_info = data.get("risk_assessment", {})
    actual_class = risk_info.get("dark_vessel_classification") or risk_info.get("classification")
    expected_class = scenario.get("expected_classification")

    if expected_class:
        assert actual_class == expected_class, (
            f"Scenario {scenario['scenario_id']} expected classification {expected_class}, got {actual_class}"
        )

    # Check threat tier
    report = data.get("final_report") or {}
    actual_tier = report.get("threat_tier")
    expected_tier = scenario.get("expected_threat_tier")
    if expected_tier:
        if expected_tier in ["HIGH", "CRITICAL"]:
            assert actual_tier in ["HIGH", "CRITICAL", "SEVERE"], (
                f"Scenario {scenario['scenario_id']} expected high tier, got {actual_tier}"
            )
        else:
            assert actual_tier == expected_tier, (
                f"Scenario {scenario['scenario_id']} expected {expected_tier}, got {actual_tier}"
            )
