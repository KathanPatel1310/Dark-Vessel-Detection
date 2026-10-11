"""Brief-style derivations: score breakdown, verdict phrase, and the plain-language checks table."""

from typing import Any, Dict, List, Optional

from src.reporting.dossier import _features_obj
from src.schemas.geospatial import GeoContext


def score_breakdown(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Rule-by-rule build-up of the dark-vessel probability.

    Mirrors MaritimeRiskScorer.evaluate_dark_vessel_probability; a test asserts the final value equals the
    production scorer's, so any drift in the rules is caught.
    """
    feats = _features_obj(ctx)
    if feats is None or not ctx.get("geo_context"):
        return {"rows": [], "final": None}
    geo = GeoContext.model_validate(ctx["geo_context"])
    notes = ctx.get("degradation_notes") or []
    sar, ais, fusion = feats.sar, feats.ais, feats.fusion
    rows: List[Dict[str, Any]] = []
    cum = 0.0

    def add(label: str, delta: Optional[float]) -> None:
        nonlocal cum
        cum = round(cum + (delta or 0.0), 4)
        rows.append({"label": label, "delta": delta, "cumulative": max(0.0, min(1.0, cum))})

    if fusion.is_spatially_correlated:
        rows.append({"label": "Matches an AIS broadcast", "delta": None, "cumulative": 0.05})
        return {"rows": rows, "final": 0.05}

    add("Starting point for an unmatched radar target", 0.50)
    length = sar.length_m
    if length < 30.0:
        add(f"Small craft ({length:.0f} m), AIS-exempt", -0.35)
        if geo.distance_to_coast_km < 30.0:
            final = round(max(0.05, cum), 2)
            rows.append({"label": "Within 30 km of coast: exempt class", "delta": None, "cumulative": final})
            return {"rows": rows, "final": final}
    elif length >= 100.0:
        add(f"Commercial-size hull ({length:.0f} m); AIS mandatory", 0.30)
    if geo.in_coverage and geo.distance_to_coast_km > 100.0:
        add(f"Far offshore ({geo.distance_to_coast_km:.0f} km)", 0.15)
    if geo.in_coverage and geo.distance_to_sts_zone_km and geo.distance_to_sts_zone_km < 80.0:
        add(f"Near a ship-to-ship corridor ({geo.distance_to_sts_zone_km:.0f} km)", 0.15)
    if ais and ais.current_gap_duration_hours >= 12.0:
        add(f"AIS silent for {ais.current_gap_duration_hours:.0f} h", 0.10)
    if any(k in str(n).lower() for n in notes for k in ("blind zone", "simulate_ais_offline", "blackout", "shadow")):
        capped = max(0.40, min(0.65, cum - 0.30))
        add("Sensor blackout noted: capped to the shadow-zone band", round(capped - cum, 4))
        return {"rows": rows, "final": round(capped, 2)}
    final = round(min(0.98, max(0.05, cum)), 2)
    if final != round(cum, 2):
        add("Clamped to the allowed range", round(final - cum, 4))
    return {"rows": rows, "final": final}


VERDICT_PHRASES = {
    "CORRELATED_BENIGN": "explained by AIS",
    "DELIBERATE_DARK_EVASION": "possible dark vessel",
    "AIS_SHADOW_ZONE": "unmatched, AIS gap likely",
    "SMALL_CRAFT_EXEMPT": "small craft, AIS-exempt",
    "SPOOFING_ANOMALY": "possible spoof",
}


def verdict(ctx: Dict[str, Any]) -> Dict[str, str]:
    risk = ctx.get("risk_assessment") or {}
    sanc = ctx.get("sanctions") or {}
    det = ctx.get("detection") or {}
    ais = ctx.get("ais_used") or {}
    if ais.get("vessel_name"):
        subject = str(ais["vessel_name"])
    else:
        subject = "Radar contact"
    phrase = "sanctions registry match" if sanc.get("is_sanctioned") else VERDICT_PHRASES.get(risk.get("dark_vessel_classification", ""), "assessment")
    tier = (ctx.get("report") or {}).get("threat_tier", "—")
    return {"subject": subject, "phrase": phrase, "tier": tier, "tag": f"THREAT TIER: {tier}"}


def checks(ctx: Dict[str, Any], ledger_check: Dict[str, Any]) -> List[Dict[str, str]]:
    """Plain-language list of what fired, what was normal, and what could not be checked."""
    det, geo, sanc = ctx.get("detection") or {}, ctx.get("geo_context") or {}, ctx.get("sanctions") or {}
    fusion = (ctx.get("features") or {}).get("fusion") or {}
    corr = bool(fusion.get("is_spatially_correlated"))
    conf = det.get("confidence") or 0.0
    n = len(ctx.get("degradation_notes") or [])
    return [
        {"check": "AIS correlation", "result": "Normal" if corr else "Fired",
         "here": "The radar target matches an AIS broadcast within the 15 km / 60 min gate." if corr else "No AIS broadcast matched the radar target within the 15 km / 60 min gate."},
        {"check": "Sanctions registries", "result": "Fired" if sanc.get("is_sanctioned") else "Normal",
         "here": f"Registry match on {sanc.get('query_target')}." if sanc.get("is_sanctioned") else "No OFAC or UN entry matched the identifiers available."},
        {"check": "Detector confidence", "result": "Normal" if conf >= 0.8 else "Weak",
         "here": f"Confidence {conf:.2f}; target-to-clutter ratio {det.get('target_clutter_ratio_db') or 0:.1f} dB."},
        {"check": "Jurisdiction data", "result": "Normal" if geo.get("in_coverage", True) else "Could not check",
         "here": "Position is inside the bundled Arabian Sea dataset." if geo.get("in_coverage", True) else "Position is outside the bundled Arabian Sea EEZ and corridor dataset."},
        {"check": "Evidence completeness", "result": "Normal" if n == 0 else "Degraded",
         "here": "Every evidence source was available." if n == 0 else f"{n} condition(s) degraded the run; see the workflow section."},
        {"check": "Human review", "result": "Required" if ctx.get("human_in_the_loop_required") else "Not required",
         "here": f"{len(ctx.get('hitl_decisions') or [])} analyst decision(s) recorded." if ctx.get("human_in_the_loop_required") else "The risk gate did not require a person to decide."},
        {"check": "Audit ledger", "result": "Normal" if ledger_check.get("valid") else "Broken",
         "here": f"{ledger_check.get('length', 0)} entries; hash chain {'verified' if ledger_check.get('valid') else 'failed at entry ' + str(ledger_check.get('broken_at'))}."},
    ]
