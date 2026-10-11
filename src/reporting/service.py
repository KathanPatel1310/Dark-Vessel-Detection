"""Orchestrates dossier generation: evidence -> figures -> narrative -> PDF."""

from typing import Any, Dict, List, Optional, Tuple

from src.reporting import brief
from src.reporting import figures as fg
from src.reporting import narrative as nv
from src.reporting.dossier import build_dossier
from src.reporting.pdf import render
from src.utils.logger import setup_logger

logger = setup_logger("report_service")


def _load_chip(chip_id: Optional[str]) -> Any:
    if not chip_id:
        return None
    try:
        from src.data.real_cases import _detect
        chip, _ = _detect(chip_id)
        return chip
    except Exception as e:
        logger.warning(f"Could not load chip {chip_id} for dossier imagery: {e}")
        return None


def build_figures(d: Dict[str, Any]) -> Dict[str, Optional[bytes]]:
    ctx = d["ctx"]
    req = ctx.get("request") or {}
    det = ctx.get("detection") or {}
    figs: Dict[str, Optional[bytes]] = {}

    def safe(name: str, fn) -> None:
        try:
            figs[name] = fn()
        except Exception as e:  # one broken figure must not sink the whole report
            logger.warning(f"Figure '{name}' failed: {e}")
            figs[name] = None

    chip = _load_chip(req.get("chip_id"))
    alld = req.get("all_detections") or [det]
    safe("chip", lambda: fg.chip_panels(chip, alld, det.get("detection_id")))
    safe("hist", lambda: fg.clutter_histogram(chip, det))
    safe("schematic", lambda: fg.schematic_hull(det) if not req.get("chip_id") else None)
    safe("map", lambda: fg.tactical_map(det, ctx.get("ais_used"), ctx.get("geo_context") or {}, (ctx.get("forecast") or {}).get("extrapolated_waypoints") or [], req.get("historical_gaps") or []))
    safe("gaps", lambda: fg.ais_gap_chart(req.get("historical_gaps") or []))
    safe("cf", lambda: fg.counterfactual_bars(d["counterfactuals"]))
    safe("sens", lambda: fg.sensitivity_curve(d["sensitivity_curve"], d["baseline_point"]) if d["baseline_point"] else None)
    safe("flow", lambda: fg.workflow_diagram(ctx.get("execution_trace") or []))
    safe("lat", lambda: fg.latency_chart(ctx.get("execution_trace") or []))
    return figs


def generate_pdf(ctx: Dict[str, Any], ledger: List[Dict[str, Any]], catalog: List[Dict[str, Any]], inventory: Dict[str, Any], use_llm: bool = False) -> Tuple[bytes, Dict[str, Any]]:
    """Returns (pdf_bytes, info) where info reports which narrative producer was used."""
    d = build_dossier(ctx, ledger, catalog, inventory)
    d["breakdown"] = brief.score_breakdown(ctx)
    d["verdict"] = brief.verdict(ctx)
    d["checks"] = brief.checks(ctx, d["ledger_check"])
    narrative = nv.build_narrative(d["facts"], catalog, ctx.get("hitl_decisions"), use_llm)
    figs = build_figures(d)
    pdf = render(d, narrative, figs)
    return pdf, {"narrative": narrative["generated_by"], "issues": narrative.get("issues", []), "evidence_sha256": d["evidence_hash"], "figures_missing": [k for k, v in figs.items() if v is None]}
