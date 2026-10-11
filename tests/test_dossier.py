"""Tests for the exhaustive PDF dossier: evidence assembly, narrative verification, and export."""

import pytest
from fastapi.testclient import TestClient

from src.api.server import app, get_meta
from src.data import real_cases
from src.reporting import narrative as nv
from src.reporting.dossier import build_dossier
from src.schemas.features import SARFeatures, AISFeatures, GeospatialFeatures, HistoricalFeatures, FusionFeatures

client = TestClient(app)


def _investigate_synthetic(scenario_id="SCN-DARK-001"):
    sc = client.get(f"/api/scenarios/{scenario_id}").json()
    res = client.post("/api/investigate", json={
        "sar_detection": sc["sar_detection"], "matched_ais": sc["ais_observation"], "historical_gaps": sc.get("historical_gaps", []),
        "scenario_id": scenario_id, "provenance": sc.get("provenance")})
    assert res.status_code == 200
    return res.json()


def test_pdf_export_for_synthetic_scenario_is_a_real_multipage_pdf():
    body = _investigate_synthetic()
    rid = body["final_report"]["report_id"]
    r = client.get(f"/api/report/{rid}/export", params={"format": "pdf"})
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")
    assert r.content.count(b"/Type /Page\n") + r.content.count(b"/Type /Page ") >= 12
    assert r.headers["x-narrative"] == "RULE_BASED"
    assert "attachment" in r.headers["content-disposition"]


@pytest.mark.skipif(not real_cases.list_cases(), reason="real chips not present")
def test_pdf_export_for_real_chip_embeds_imagery_and_records_audit():
    cid = real_cases.list_cases()[0]["chip_id"]
    case = client.get(f"/api/cases/real/{cid}", params={"withhold_ais": True}).json()
    body = client.post("/api/investigate", json={
        "sar_detection": case["sar_detection"], "matched_ais": None, "chip_id": cid, "simulate_ais_offline": True,
        "ground_truth": case["ground_truth"], "all_detections": case["all_detections"], "provenance": case["provenance"]}).json()
    r = client.get(f"/api/report/{body['final_report']['report_id']}/export", params={"format": "pdf"})
    assert r.status_code == 200 and len(r.content) > 500_000  # embedded chip + figures
    ledger = client.get("/api/audit").json()["ledger"]
    assert any(e["action"] == "DOSSIER_EXPORTED" for e in ledger)


def test_trace_latency_is_measured_for_every_node():
    body = _investigate_synthetic()
    assert body["execution_trace"], "trace missing"
    assert all(t.get("latency_ms") is not None for t in body["execution_trace"])


def test_dossier_covers_all_features_and_runs_counterfactuals():
    _investigate_synthetic()
    from src.api.server import CASE_CONTEXTS, AUDIT_LEDGER, get_data_inventory
    ctx = next(iter(CASE_CONTEXTS.values()))
    d = build_dossier(ctx, AUDIT_LEDGER, get_meta()["citation_catalog"], get_data_inventory())
    expected = sum(len(m.model_fields) for m in (SARFeatures, AISFeatures, GeospatialFeatures, HistoricalFeatures, FusionFeatures))
    assert len(d["features"]) == expected == get_meta()["feature_count"]
    labels = [r["label"] for r in d["counterfactuals"]]
    assert "Baseline (as investigated)" in labels and len(labels) >= 6
    assert d["ledger_check"]["valid"] is True
    assert any(l["triggered"] for l in d["legal"]) or ctx["report"]["statutory_violations"]
    assert len(d["evidence_hash"]) == 64


def test_faithfulness_check_rejects_invented_numbers_and_statutes():
    facts = {"length_m": 245.0, "latitude": 21.38, "statutes": ["SOLAS Chapter V, Regulation 19"], "dark_vessel_probability": 0.9}
    catalog = get_meta()["citation_catalog"]
    ok, _ = nv.check_faithfulness("Hull of 245 m at 21.38 degrees, p = 0.90, SOLAS Regulation 19 applies.", facts, catalog)
    assert ok
    bad, issues = nv.check_faithfulness("Hull of 312 m was seen under UNCLOS Article 999.", facts, catalog)
    assert not bad and any("312" in i for i in issues) and any("999" in i for i in issues)


def test_template_narrative_passes_its_own_faithfulness_check():
    _investigate_synthetic()
    from src.api.server import CASE_CONTEXTS
    from src.reporting.dossier import build_facts
    ctx = next(iter(CASE_CONTEXTS.values()))
    facts = build_facts(ctx)
    text = " ".join(nv.template_narrative(facts)["paragraphs"])
    ok, issues = nv.check_faithfulness(text, facts, get_meta()["citation_catalog"])
    assert ok, issues


def test_llm_request_falls_back_to_verified_template_when_model_unavailable(monkeypatch):
    monkeypatch.setattr(nv, "llm_narrative", lambda *a, **k: (_ for _ in ()).throw(nv.LlmUnavailable("model files missing")))
    facts = {"detection_id": "X", "latitude": 1.0, "longitude": 2.0, "length_m": 100.0, "width_m": 20.0, "radar_confidence": 0.9, "ais_status": "NON_TRANSMITTING",
             "correlated_mmsi": None, "jurisdiction": "Intl", "distance_to_coast_km": 10.0, "in_dataset_coverage": True, "sanctions_hit": False,
             "classification": "AIS_SHADOW_ZONE", "dark_vessel_probability": 0.5, "anomaly_score": 0.4, "threat_tier": "MEDIUM", "degradation_notes": [], "statutes": []}
    out = nv.build_narrative(facts, [], None, use_llm=True)
    assert out["generated_by"] == "RULE_BASED" and any("AI narrative skipped" in i for i in out["issues"])


def _gpu_llm_ready():
    try:
        import torch
        return nv.llm_status()["available"] and torch.cuda.is_available()
    except Exception:
        return False


@pytest.mark.skipif(not _gpu_llm_ready(), reason="fine-tuned Qwen files or a CUDA GPU are not available")
def test_llm_summary_is_verified_against_evidence_when_model_is_available():
    from src.api.server import CASE_CONTEXTS
    from src.reporting.dossier import build_facts
    _investigate_synthetic()
    facts = build_facts(next(iter(CASE_CONTEXTS.values())))
    out = nv.llm_narrative(facts, get_meta()["citation_catalog"])
    assert out["generated_by"] == "LLM_VERIFIED" and out["paragraphs"]
    ok, issues = nv.check_faithfulness(" ".join(out["paragraphs"]), facts, get_meta()["citation_catalog"])
    assert ok, issues


def test_faithfulness_check_rejects_wrong_tier_classification_and_jurisdiction():
    facts = {"threat_tier": "SEVERE", "classification": "CORRELATED_BENIGN", "jurisdiction": "Oman", "length_m": 274.0, "statutes": []}
    cat = get_meta()["citation_catalog"]
    ok, _ = nv.check_faithfulness("Ship length 274.0m. Jurisdiction: Oman. SEVERE tier. CORRELATED_BENIGN.", facts, cat)
    assert ok
    bad, issues = nv.check_faithfulness("Ship length 274.0m. Anomaly (CRITICAL Tier). Classified DELIBERATE_DARK_EVASION. Jurisdiction: Iran.", facts, cat)
    assert not bad
    joined = " ".join(issues)
    assert "CRITICAL" in joined and "DELIBERATE_DARK_EVASION" in joined and "Iran" in joined
