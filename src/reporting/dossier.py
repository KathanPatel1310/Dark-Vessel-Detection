"""Evidence assembly for the exhaustive PDF dossier.

Everything here is deterministic code: it reads the stored investigation context, re-runs the
deterministic scorer for counterfactuals, and derives the legal mapping and alternative
hypotheses from explicit conditions. Language models never touch numbers or citations.
"""

import copy
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.analytics.risk_scorer import MaritimeRiskScorer
from src.schemas.features import EngineeredFeatures, SARFeatures, AISFeatures, GeospatialFeatures, HistoricalFeatures, FusionFeatures
from src.schemas.geospatial import GeoContext

DOMAIN_MODELS = {"sar": SARFeatures, "ais": AISFeatures, "geospatial": GeospatialFeatures, "historical": HistoricalFeatures, "fusion": FusionFeatures}

# Where each engineered feature comes from; formulas are documented in docs/ and the feature modules.
FORMULAS: Dict[str, str] = {
    "aspect_ratio": "length_m / width_m",
    "compactness": "perimeter^2 / (4 * pi * area)",
    "target_to_clutter_ratio_db": "mean target dB - mean clutter dB",
    "spatial_discrepancy_km": "haversine(SAR position, AIS position)",
    "temporal_difference_minutes": "|t_SAR - t_AIS| in minutes",
    "dimension_mismatch_ratio": "|L_SAR − L_AIS| / L_AIS",
    "heading_discrepancy_deg": "min(|SAR heading - COG|, 360 - |SAR heading - COG|)",
    "heading_variance": "1 - |sum of unit heading vectors| / N (circular variance)",
    "trajectory_curvature": "path length / endpoint displacement",
    "candidate_identity_score": "weighted spatial + temporal + dimension agreement",
}


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "unknown"


def canonical_hash(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def provenance_of(ctx: Dict[str, Any]) -> Dict[str, str]:
    req = ctx.get("request", {})
    given = req.get("provenance") or {}
    is_real_chip = bool(req.get("chip_id"))
    geo = ctx.get("geo_context") or {}
    ais_state = given.get("ais") or ("REAL" if (is_real_chip and ctx.get("ais_used")) else ("UNAVAILABLE" if not ctx.get("ais_used") else "SYNTHETIC"))
    return {
        "Radar imagery": "REAL" if is_real_chip else "SYNTHETIC",
        "Radar measurements": "DERIVED" if is_real_chip else "SYNTHETIC",
        "AIS": ais_state,
        "Sanctions registries": "REAL",
        "Jurisdiction (EEZ / STS)": "DERIVED" if geo.get("in_coverage", True) else "UNAVAILABLE",
        "Historical features": "HEURISTIC",
        "Risk classification": "HEURISTIC",
        "Trajectory forecast": "DERIVED",
    }


def _features_obj(ctx: Dict[str, Any]) -> Optional[EngineeredFeatures]:
    try:
        return EngineeredFeatures.model_validate(ctx["features"])
    except Exception:
        return None


def feature_rows(ctx: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Every engineered feature: domain, name, value, description, formula, provenance."""
    feats = ctx.get("features") or {}
    prov = provenance_of(ctx)
    domain_prov = {"sar": prov["Radar measurements"], "ais": prov["AIS"], "geospatial": prov["Jurisdiction (EEZ / STS)"],
                   "historical": "HEURISTIC", "fusion": "DERIVED"}
    rows: List[Dict[str, Any]] = []
    has_ais = bool(ctx.get("ais_used")) or bool((ctx.get("request") or {}).get("historical_gaps"))
    no_ais_masked = {"spatial_discrepancy_km", "temporal_difference_minutes", "candidate_identity_score"}
    for domain, model in DOMAIN_MODELS.items():
        block = feats.get(domain)
        for name, field in model.model_fields.items():
            if block is None:
                value, note = None, "not computed (no AIS track available)" if domain == "ais" else "not computed"
            elif (domain == "ais" and not has_ais) or (domain == "fusion" and name in no_ais_masked and not ctx.get("ais_used")):
                value, note = None, "n/a — no AIS candidate (placeholder in the feature vector)"
            else:
                value = block.get(name)
                note = "" if value is not None else "unavailable for this case"
            rows.append({"domain": domain, "name": name, "value": value, "description": field.description or "",
                         "formula": FORMULAS.get(name, ""), "provenance": domain_prov[domain], "note": note})
    return rows


def counterfactuals(ctx: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Tuple[float, float]], Optional[Tuple[float, float]]]:
    """Re-score the target with the production scorer under explicit what-if perturbations."""
    feats = _features_obj(ctx)
    if feats is None or not ctx.get("geo_context"):
        return [], [], None
    geo = GeoContext.model_validate(ctx["geo_context"])
    notes = ctx.get("degradation_notes") or []

    def score(f: EngineeredFeatures, g: GeoContext, n: Optional[List[str]]) -> Tuple[float, str]:
        p, tag, _ = MaritimeRiskScorer.evaluate_dark_vessel_probability(f, g, n)
        return p, tag

    base_p, base_tag = score(feats, geo, notes)
    rows = [{"label": "Baseline (as investigated)", "probability": base_p, "classification": base_tag, "change": "—"}]

    f = copy.deepcopy(feats); f.fusion.is_spatially_correlated = True
    p, t = score(f, geo, notes); rows.append({"label": "AIS correlation found", "probability": p, "classification": t, "change": "fusion.is_spatially_correlated = True"})

    f = copy.deepcopy(feats); f.fusion.is_spatially_correlated = False
    p, t = score(f, geo, notes); rows.append({"label": "No AIS correlation", "probability": p, "classification": t, "change": "fusion.is_spatially_correlated = False"})

    f = copy.deepcopy(feats); f.sar.length_m = 25.0
    p, t = score(f, geo, notes); rows.append({"label": "Vessel only 25 m long", "probability": p, "classification": t, "change": "sar.length_m = 25"})

    f = copy.deepcopy(feats); f.sar.length_m = 250.0
    p, t = score(f, geo, notes); rows.append({"label": "Vessel 250 m long", "probability": p, "classification": t, "change": "sar.length_m = 250"})

    g2 = geo.model_copy(update={"distance_to_coast_km": 20.0, "in_coverage": True})
    p, t = score(feats, g2, notes); rows.append({"label": "20 km from coast", "probability": p, "classification": t, "change": "distance_to_coast_km = 20"})

    g3 = geo.model_copy(update={"distance_to_coast_km": 250.0, "in_coverage": True})
    p, t = score(feats, g3, notes); rows.append({"label": "250 km offshore", "probability": p, "classification": t, "change": "distance_to_coast_km = 250"})

    p, t = score(feats, geo, [])
    rows.append({"label": "No degradation notes", "probability": p, "classification": t, "change": "degradation_notes = []"})

    curve: List[Tuple[float, float]] = []
    for L in range(10, 321, 10):
        f = copy.deepcopy(feats); f.sar.length_m = float(L)
        curve.append((float(L), score(f, geo, notes)[0]))
    return rows, curve, (feats.sar.length_m, base_p)


def alternative_hypotheses(ctx: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Benign / alternative explanations, each with evidence for, against, and what would settle it."""
    feats = ctx.get("features") or {}
    sar = feats.get("sar") or {}
    fusion = feats.get("fusion") or {}
    ais = feats.get("ais") or {}
    geo = ctx.get("geo_context") or {}
    det = ctx.get("detection") or {}
    L = sar.get("length_m", det.get("length_m", 0.0))
    correlated = bool(fusion.get("is_spatially_correlated"))
    out: List[Dict[str, Any]] = []

    out.append({
        "name": "Legitimately small craft exempt from AIS",
        "for": [f"Measured length {L:.0f} m" + (" is below the 30 m rule-of-thumb exemption." if L < 30 else " is above the exemption threshold.")],
        "against": ([] if L < 30 else ["Hull is far larger than craft normally exempt under SOLAS Ch. V Reg. 19."]) + [
            "Length is estimated from an axis-aligned detector box at 10 m pixel spacing (±10 m quantisation)."],
        "settle": "Optical or FLIR confirmation, or a higher-resolution SAR acquisition.",
        "weight": "LOW" if L >= 50 else ("HIGH" if L < 30 else "MEDIUM"),
    })
    out.append({
        "name": "AIS coverage gap or satellite blind zone",
        "for": [n for n in (ctx.get("degradation_notes") or []) if "ais" in n.lower() or "blind" in n.lower()] or ["No explicit coverage-gap note was recorded."],
        "against": ["No independent AIS-coverage map is bundled, so coverage cannot be verified here."],
        "settle": "Query terrestrial/satellite AIS receiver coverage for the acquisition time.",
        "weight": "MEDIUM" if (ctx.get("degradation_notes") and not correlated) else "LOW",
    })
    out.append({
        "name": "AIS spoofing or position error (vessel is transmitting, but wrongly)",
        "for": ([f"Nearest AIS report is {fusion.get('spatial_discrepancy_km', 0):.1f} km away."] if (fusion and ctx.get("ais_used")) else []) or ["No candidate AIS report to compare."],
        "against": ["Spoofing cannot be distinguished from absence using one SAR snapshot."],
        "settle": "Multi-pass SAR + AIS track continuity analysis.",
        "weight": "LOW",
    })
    out.append({
        "name": "Detector false positive (sea clutter, platform, wake)",
        "for": [f"Detector confidence {det.get('confidence', 0):.2f}.", f"Target-to-clutter ratio {sar.get('target_to_clutter_ratio_db', 0) or 0:.1f} dB."],
        "against": ["Confidence and contrast are well above typical clutter returns." if (det.get("confidence", 0) or 0) > 0.8 else "Moderate confidence leaves room for a spurious return."],
        "settle": "Review the raw chip; check neighbouring acquisitions.",
        "weight": "LOW" if (det.get("confidence", 0) or 0) > 0.8 else "MEDIUM",
    })
    if ctx.get("request", {}).get("chip_id") and ctx.get("request", {}).get("simulate_ais_offline"):
        gt = ctx.get("request", {}).get("ground_truth_ais") or {}
        out.append({
            "name": "Counterfactual test artefact (AIS was withheld on purpose)",
            "for": [f"This case uses a real radar chip whose true AIS (MMSI {gt.get('mmsi', '?')}, {gt.get('vessel_name', 'unknown')}) was hidden."],
            "against": [],
            "settle": "None required — this is the intended test condition, not an observed evasion.",
            "weight": "CERTAIN",
        })
    return out


def limitations(ctx: Dict[str, Any]) -> List[str]:
    prov = provenance_of(ctx)
    geo = ctx.get("geo_context") or {}
    items = [
        "A radar detection alone cannot show that a vessel is deliberately hiding; the output is a probability, not a finding of fact.",
        "Length, beam and heading are estimated from detector boxes at 10 m pixel spacing and carry material uncertainty.",
        "The risk score is a rule-based heuristic, not a calibrated statistical model; thresholds are documented in Section 4 of this report.",
        "Historical features (flag/name changes, route anomaly, past STS) are heuristic placeholders unless an AIS history was supplied.",
        "Single-snapshot assessment: no multi-pass confirmation, wake analysis or Doppler speed estimate.",
    ]
    if not geo.get("in_coverage", True):
        items.append("The position is outside the bundled Arabian Sea EEZ/STS dataset; no jurisdictional or corridor reasoning was applied.")
    if prov["Radar imagery"] == "SYNTHETIC":
        items.append("This case is a synthetic benchmark scenario; no real radar imagery underlies it.")
    if prov["AIS"] in ("UNAVAILABLE", "SYNTHETIC"):
        items.append("AIS evidence is " + ("absent or withheld." if prov["AIS"] == "UNAVAILABLE" else "synthetic."))
    return items


def legal_mapping(ctx: Dict[str, Any], catalog: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Cited statutes with article text and the evidence that triggered each."""
    rep = ctx.get("report") or {}
    cited = rep.get("statutory_violations") or []
    feats = ctx.get("features") or {}
    sar = feats.get("sar") or {}
    fusion = feats.get("fusion") or {}
    geo = ctx.get("geo_context") or {}
    sanc = ctx.get("sanctions") or {}
    by_id = {c["id"]: c for c in catalog}

    def pick(text: str) -> Optional[str]:
        t = text.lower()
        if "solas" in t: return "SOLAS_V_19"
        if "73" in t and "unclos" in t: return "UNCLOS_ART_73"
        if "110" in t: return "UNCLOS_ART_110"
        if "92" in t and "unclos" in t: return "UNCLOS_ART_92"
        if "ofac" in t or "sanction" in t: return "OFAC_IEEPA"
        return None

    why = {
        "SOLAS_V_19": f"Radar length {sar.get('length_m', 0):.0f} m with no AIS correlation: AIS carriage is mandatory for commercial vessels of this size.",
        "UNCLOS_ART_73": f"Position is inside the sovereign EEZ of {geo.get('eez_country')} and the vessel is not transmitting.",
        "OFAC_IEEPA": "The sanctions screen returned a confirmed registry match." if sanc.get("is_sanctioned") else "Cited by the report engine.",
    }
    rows, seen = [], set()
    for text in cited:
        cid = pick(text)
        entry = by_id.get(cid) if cid else None
        rows.append({"citation": text, "catalog_id": cid, "title": entry["title"] if entry else text, "statute": entry["statute"] if entry else "(no catalogue entry — text shown as cited)",
                     "link": entry.get("link") if entry else None, "why": why.get(cid, "Cited by the deterministic report engine."), "triggered": True})
        if cid: seen.add(cid)
    for cid, entry in by_id.items():
        if cid not in seen:
            reason = {
                "SOLAS_V_19": "Not cited: vessel is AIS-correlated or below the commercial-size threshold.",
                "UNCLOS_ART_73": "Not cited: position is not inside a mapped sovereign EEZ or the vessel is transmitting.",
                "UNCLOS_ART_92": "Not cited: no nationality/flag irregularity evidence in the inputs.",
                "UNCLOS_ART_110": "Not cited: right-of-visit grounds (stateless / piracy) are not evidenced.",
                "OFAC_IEEPA": "Not cited: no confirmed sanctions match." if not sanc.get("is_sanctioned") else "Not cited.",
            }.get(cid, "Not triggered by the evidence.")
            rows.append({"citation": entry["title"], "catalog_id": cid, "title": entry["title"], "statute": entry["statute"], "link": entry.get("link"), "why": reason, "triggered": False})
    return rows


def verify_ledger(ledger: List[Dict[str, Any]]) -> Dict[str, Any]:
    prev = "0" * 64
    for e in ledger:
        raw = f"{e['index']}:{e['timestamp']}:{e['action']}:{e['operator']}:{json.dumps(e['details'], sort_keys=True, default=str)}:{prev}"
        if e["prev_hash"] != prev or hashlib.sha256(raw.encode("utf-8")).hexdigest() != e["hash"]:
            return {"valid": False, "broken_at": e["index"], "length": len(ledger), "head": ledger[-1]["hash"] if ledger else None}
        prev = e["hash"]
    return {"valid": True, "broken_at": None, "length": len(ledger), "head": prev}


def timeline(ctx: Dict[str, Any]) -> List[Dict[str, str]]:
    det = ctx.get("detection") or {}
    ais = ctx.get("ais_used")
    events = [{"time": det.get("timestamp", ""), "event": f"SAR acquisition ({det.get('scene_id', 'unknown scene')}); detection {det.get('detection_id', '')}"}]
    if ais:
        events.append({"time": ais.get("timestamp", ""), "event": f"AIS report: {ais.get('vessel_name') or ais.get('mmsi')} (MMSI {ais.get('mmsi')}), SOG {ais.get('sog')} kn, COG {ais.get('cog')}°"})
    for g in (ctx.get("request") or {}).get("historical_gaps") or []:
        events.append({"time": g.get("gap_start", ""), "event": f"AIS gap begins ({g.get('duration_hours', 0):.1f} h){' — flagged suspicious' if g.get('is_suspicious') else ''}"})
        if g.get("gap_end"):
            events.append({"time": g["gap_end"], "event": "AIS gap ends / last gap-window timestamp"})
    events.append({"time": ctx.get("created_at", ""), "event": f"Investigation executed (mission {ctx.get('mission_id')})"})
    for w in (ctx.get("forecast") or {}).get("extrapolated_waypoints") or []:
        events.append({"time": w.get("projected_timestamp", ""), "event": f"Forecast +{w.get('projection_hours'):g} h: ({w.get('projected_lat'):.3f}, {w.get('projected_lon'):.3f}) ±{w.get('uncertainty_radius_km'):.1f} km"})
    for h in ctx.get("hitl_decisions") or []:
        events.append({"time": h.get("timestamp", ""), "event": f"Analyst decision: {h.get('disposition')}"})
    return sorted(events, key=lambda e: e["time"] or "9999")


def build_facts(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Compact evidence JSON used (a) for the narrative prompt and (b) as the faithfulness reference."""
    rep, det, geo = ctx.get("report") or {}, ctx.get("detection") or {}, ctx.get("geo_context") or {}
    risk, sanc = ctx.get("risk_assessment") or {}, ctx.get("sanctions") or {}
    fusion = (ctx.get("features") or {}).get("fusion") or {}
    return {
        "mission_id": ctx.get("mission_id"), "report_id": rep.get("report_id"), "detection_id": det.get("detection_id"),
        "latitude": det.get("latitude"), "longitude": det.get("longitude"),
        "length_m": det.get("length_m"), "width_m": det.get("width_m"), "aspect_ratio": det.get("aspect_ratio"),
        "radar_confidence": det.get("confidence"), "tcr_db": det.get("target_clutter_ratio_db"),
        "ais_status": "Active Match" if fusion.get("is_spatially_correlated") else "NON_TRANSMITTING",
        "correlated_mmsi": (ctx.get("features") or {}).get("mmsi_candidate"),
        "jurisdiction": geo.get("eez_country") or "International Waters", "distance_to_coast_km": geo.get("distance_to_coast_km"),
        "in_dataset_coverage": geo.get("in_coverage", True),
        "sanctions_hit": bool(sanc.get("is_sanctioned")), "sanctions_risk": sanc.get("overall_sanctions_risk"),
        "classification": risk.get("dark_vessel_classification"), "dark_vessel_probability": risk.get("dark_vessel_probability"),
        "anomaly_score": risk.get("overall_anomaly_score"), "threat_tier": rep.get("threat_tier"),
        "degradation_notes": ctx.get("degradation_notes") or [], "degradation_count": len(ctx.get("degradation_notes") or []), "statutes": rep.get("statutory_violations") or [],
    }


def build_dossier(ctx: Dict[str, Any], ledger: List[Dict[str, Any]], catalog: List[Dict[str, Any]], inventory: Dict[str, Any]) -> Dict[str, Any]:
    cf_rows, curve, baseline = counterfactuals(ctx)
    mission = ctx.get("mission_id")
    case_ledger = [e for e in ledger if mission and mission in json.dumps(e.get("details", {}), default=str)]
    evidence_hash = canonical_hash({k: v for k, v in ctx.items() if k != "narrative"})
    versions = {"git_sha": _git_sha(), "python": sys.version.split()[0], "platform": platform.platform()}
    try:
        import reportlab, matplotlib, numpy
        versions.update({"reportlab": reportlab.Version, "matplotlib": matplotlib.__version__, "numpy": numpy.__version__})
    except Exception:
        pass
    return {
        "ctx": ctx, "facts": build_facts(ctx), "provenance": provenance_of(ctx), "features": feature_rows(ctx),
        "counterfactuals": cf_rows, "sensitivity_curve": curve, "baseline_point": baseline,
        "hypotheses": alternative_hypotheses(ctx), "limitations": limitations(ctx), "legal": legal_mapping(ctx, catalog),
        "timeline": timeline(ctx), "case_ledger": case_ledger, "ledger_check": verify_ledger(ledger),
        "evidence_hash": evidence_hash, "versions": versions, "inventory": inventory,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
