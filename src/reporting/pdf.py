"""reportlab renderer for the exhaustive intelligence dossier."""

import io
import json
import os
from typing import Any, Dict, List, Optional

import matplotlib
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether, NextPageTemplate, PageBreak, PageTemplate, Paragraph,
                                Spacer, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

_FONT_DIR = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf")
for _name, _file in (("DV", "DejaVuSans.ttf"), ("DV-B", "DejaVuSans-Bold.ttf"), ("DV-I", "DejaVuSans-Oblique.ttf"), ("DVM", "DejaVuSansMono.ttf")):
    try:
        pdfmetrics.registerFont(TTFont(_name, os.path.join(_FONT_DIR, _file)))
    except Exception:  # fall back to built-ins if matplotlib's fonts are missing
        pass
_HAS_DV = "DV" in pdfmetrics.getRegisteredFontNames()
F, FB, FI, FM = ("DV", "DV-B", "DV-I", "DVM") if _HAS_DV else ("Helvetica", "Helvetica-Bold", "Helvetica-Oblique", "Courier")

NAVY = colors.HexColor("#0B1F3A")
CYAN = colors.HexColor("#0891B2")
GREY = colors.HexColor("#64748B")
LIGHT = colors.HexColor("#F1F5F9")
RULE = colors.HexColor("#CBD5E1")
PROV_COLOR = {"REAL": "#15803D", "DERIVED": "#0E7490", "SYNTHETIC": "#7C3AED", "HEURISTIC": "#B45309", "UNAVAILABLE": "#B91C1C"}
TIER_COLOR = {"LOW": "#15803D", "MEDIUM": "#B45309", "HIGH": "#C2410C", "SEVERE": "#B91C1C"}

S = {
    "title": ParagraphStyle("title", fontName=FB, fontSize=26, leading=30, textColor=NAVY),
    "h1": ParagraphStyle("h1", fontName=FB, fontSize=15, leading=19, textColor=NAVY, spaceBefore=4, spaceAfter=6),
    "h1b": ParagraphStyle("h1b", fontName=FB, fontSize=15, leading=19, textColor=NAVY, spaceAfter=8),
    "h2": ParagraphStyle("h2", fontName=FB, fontSize=10.5, leading=14, textColor=CYAN, spaceBefore=8, spaceAfter=3),
    "body": ParagraphStyle("body", fontName=F, fontSize=9, leading=13, alignment=TA_LEFT, spaceAfter=4),
    "small": ParagraphStyle("small", fontName=F, fontSize=7.5, leading=10, textColor=GREY),
    "cell": ParagraphStyle("cell", fontName=F, fontSize=7.6, leading=10),
    "cellb": ParagraphStyle("cellb", fontName=FB, fontSize=7.6, leading=10, textColor=colors.white),
    "mono": ParagraphStyle("mono", fontName=FM, fontSize=7, leading=9),
    "bullet": ParagraphStyle("bullet", fontName=F, fontSize=9, leading=13, leftIndent=10, bulletIndent=0, spaceAfter=2),
}


def esc(x: Any) -> str:
    return str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class M(str):
    """Marks a string as reportlab markup (everything else is escaped)."""


def _cell(x: Any) -> str:
    return str(x) if isinstance(x, M) else esc(x)


def P(text: Any, style: str = "body") -> Paragraph:
    return Paragraph(_cell(text), S[style])


def chip(tag: str) -> M:
    return M(f'<font color="{PROV_COLOR.get(tag, "#475569")}" name="{FB}" size="6.5">[{tag}]</font>')



def fmt(v: Any, nd: int = 2) -> str:
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, float):
        return f"{v:.{nd}f}"
    return str(v)


def table(header: List[str], rows: List[List[Any]], widths: List[float], zebra: bool = True) -> Table:
    data = [[Paragraph(esc(h), S["cellb"]) for h in header]]
    for r in rows:
        data.append([c if hasattr(c, "wrap") else Paragraph(_cell(c), S["cell"]) for c in r])
    t = Table(data, colWidths=widths, repeatRows=1)
    style = [("BACKGROUND", (0, 0), (-1, 0), NAVY), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("GRID", (0, 0), (-1, -1), 0.25, RULE),
             ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4), ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]
    if zebra:
        style += [("BACKGROUND", (0, i), (-1, i), LIGHT) for i in range(2, len(data), 2)]
    t.setStyle(TableStyle(style))
    return t


def kv(rows: List[List[Any]], w1: float = 55 * mm, w2: float = 115 * mm) -> Table:
    return table(["Field", "Value"], rows, [w1, w2])


def img(png: Optional[bytes], width: float) -> Optional[Image]:
    if not png:
        return None
    iw, ih = ImageReader(io.BytesIO(png)).getSize()
    return Image(io.BytesIO(png), width=width, height=width * ih / iw)


class _Doc(BaseDocTemplate):
    def __init__(self, buf, meta):
        super().__init__(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=22 * mm, bottomMargin=18 * mm,
                         title=f"Intelligence Dossier {meta['report_id']}", author="DVD-MDA", subject="Maritime intelligence dossier")
        self.meta = meta
        w, h = A4
        frame = Frame(self.leftMargin, self.bottomMargin, w - self.leftMargin - self.rightMargin, h - self.topMargin - self.bottomMargin, id="f")
        self.addPageTemplates([PageTemplate(id="cover", frames=[frame], onPage=self._cover), PageTemplate(id="body", frames=[frame], onPage=self._page)])

    def _cover(self, c, d):
        c.saveState(); c.setFillColor(NAVY); c.rect(0, A4[1] - 14 * mm, A4[0], 14 * mm, stroke=0, fill=1)
        c.setFillColor(colors.white); c.setFont(FB, 9); c.drawString(18 * mm, A4[1] - 9 * mm, "DVD-MDA · MARITIME INTELLIGENCE DOSSIER")
        c.restoreState()

    def _page(self, c, d):
        c.saveState(); w, h = A4
        c.setFillColor(NAVY); c.rect(0, h - 11 * mm, w, 11 * mm, stroke=0, fill=1)
        c.setFillColor(colors.white); c.setFont(FB, 7.5)
        c.drawString(18 * mm, h - 7 * mm, f"DVD-MDA · {self.meta['report_id']} · {self.meta['case']}")
        c.setFillColor(colors.HexColor(TIER_COLOR.get(self.meta["tier"], "#475569"))); c.drawRightString(w - 18 * mm, h - 7 * mm, f"THREAT TIER: {self.meta['tier']}")
        c.setFillColor(GREY); c.setFont(F, 6.5)
        c.drawString(18 * mm, 10 * mm, f"Academic research prototype — assessment is a hypothesis for analyst review, not a finding of fact. SHA-256 {self.meta['hash'][:16]}…")
        c.drawRightString(w - 18 * mm, 10 * mm, f"Page {d.page}")
        c.restoreState()

    def afterFlowable(self, fl):
        if isinstance(fl, Paragraph) and fl.style.name == "h1":
            text = fl.getPlainText()
            key = "sec-" + "".join(ch if ch.isalnum() else "-" for ch in text)[:40]  # stable across multiBuild passes
            self.canv.bookmarkPage(key); self.canv.addOutlineEntry(text, key, 0, 0)
            self.notify("TOCEntry", (0, text, self.page, key))


def render(d: Dict[str, Any], narrative: Dict[str, Any], figs: Dict[str, Optional[bytes]]) -> bytes:
    ctx = d["ctx"]; facts = d["facts"]; rep = ctx.get("report") or {}; det = ctx.get("detection") or {}
    risk = ctx.get("risk_assessment") or {}; geo = ctx.get("geo_context") or {}; sanc = ctx.get("sanctions") or {}
    feats = ctx.get("features") or {}; fusion = feats.get("fusion") or {}; ais_rec = ctx.get("ais_used")
    forecast = ctx.get("forecast") or {}; req = ctx.get("request") or {}
    tier = rep.get("threat_tier", "—")
    meta = {"report_id": rep.get("report_id", ctx.get("mission_id")), "case": req.get("scenario_id") or req.get("chip_id") or ctx.get("mission_id"), "tier": tier, "hash": d["evidence_hash"]}
    W = 174 * mm
    buf = io.BytesIO()
    doc = _Doc(buf, meta)
    el: List[Any] = []

    def sec(title: str):
        el.append(Paragraph(title, S["h1"]))

    def add_img(key: str, width: float = W, note: str = ""):
        im = img(figs.get(key), width)
        if im is not None:
            el.append(im)
        elif note:
            el.append(P(note, "small"))
        el.append(Spacer(1, 4))

    # ---- 0. Cover -------------------------------------------------------------------------------
    el += [Spacer(1, 26 * mm), Paragraph("Maritime Intelligence Dossier", S["title"]), Spacer(1, 3),
           P(f"Report {meta['report_id']}  ·  Case {meta['case']}  ·  Mission {ctx.get('mission_id')}", "body"), Spacer(1, 8)]
    banner = Table([[Paragraph(f'<font color="white" name="{FB}" size="13">THREAT TIER: {tier}</font>', S["body"]),
                     Paragraph(f'<font color="white" name="{F}" size="9">{esc(fmt(risk.get("dark_vessel_classification")))} · p = {fmt(risk.get("dark_vessel_probability"))} · anomaly {fmt(risk.get("overall_anomaly_score"))}</font>', S["body"])]],
                   colWidths=[W * 0.35, W * 0.65])
    banner.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(TIER_COLOR.get(tier, "#475569"))), ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8), ("LEFTPADDING", (0, 0), (-1, -1), 8)]))
    el += [banner, Spacer(1, 8)]
    el.append(P(narrative["paragraphs"][0] if narrative.get("paragraphs") else "", "body"))
    el.append(Paragraph("Data integrity at a glance", S["h2"]))
    el.append(table(["Input", "Provenance"], [[k, Paragraph(chip(v), S["cell"])] for k, v in d["provenance"].items()], [W * 0.6, W * 0.4]))
    el.append(Spacer(1, 6))
    el.append(kv([["Generated (UTC)", d["generated_at"]], ["Investigation run (UTC)", ctx.get("created_at", "—")], ["Narrative", narrative.get("label", "")],
                  ["Human review required", fmt(ctx.get("human_in_the_loop_required"))], ["Evidence SHA-256", Paragraph(f'<font name="{FM}" size="6.5">{d["evidence_hash"]}</font>', S["cell"])],
                  ["Software", f"git {d['versions'].get('git_sha')} · Python {d['versions'].get('python')}"]]))
    el += [NextPageTemplate("body"), PageBreak()]
    toc = TableOfContents(); toc.levelStyles = [ParagraphStyle("t0", fontName=F, fontSize=9, leading=14, leftIndent=0)]
    el += [Paragraph("Contents", S["h1b"]), toc, PageBreak()]

    # ---- 1. Executive assessment ---------------------------------------------------------------
    sec("1. Executive assessment")
    el.append(P(M(f"<i>{esc(narrative.get('label', ''))}</i>"), "small"))
    for p in narrative.get("paragraphs", []):
        el.append(P(p))
    if narrative.get("rule_based_paragraphs"):
        el.append(Paragraph("Evidence detail (rule-generated from the stored evidence)", S["h2"]))
        for p in narrative["rule_based_paragraphs"]:
            el.append(P(p))
    for issue in narrative.get("issues", []):
        el.append(P(f"Note: {issue}", "small"))
    el.append(Paragraph("Key findings", S["h2"]))
    for k in narrative.get("key_findings", []):
        el.append(Paragraph(esc(k), S["bullet"], bulletText="•"))
    el.append(Paragraph("Recommended actions", S["h2"]))
    for r in rep.get("actionable_recommendations", []):
        el.append(Paragraph(esc(r), S["bullet"], bulletText="→"))
    trig = [l for l in d["legal"] if l["triggered"]]
    if trig:
        el.append(P("Legal basis: " + "; ".join(l["title"] for l in trig) + " (see §13).", "small"))
    el.append(PageBreak())

    # ---- 2. Situation & timeline ---------------------------------------------------------------
    sec("2. Situation and timeline")
    el.append(table(["Time (UTC)", "Event"], [[t["time"], t["event"]] for t in d["timeline"]], [45 * mm, W - 45 * mm]))

    # ---- 3. Target identification --------------------------------------------------------------
    sec("3. Target identification")
    unc_len = "±10 m (pixel quantisation at 10 m spacing)"
    rows = [["Length", f"{fmt(det.get('length_m'), 1)} m  {unc_len}"], ["Beam", f"{fmt(det.get('width_m'), 1)} m  ±10 m"], ["Aspect ratio L/B", fmt(det.get("aspect_ratio"))],
            ["Heading (estimated)", f"{fmt(det.get('heading_deg'), 1)}°  (from detector box; coarse)"], ["Peak / mean backscatter", f"{fmt(det.get('peak_backscatter_db'))} / {fmt(det.get('mean_backscatter_db'))} dB (uncalibrated)"],
            ["Sea clutter mean", f"{fmt(det.get('background_mean_db'))} dB"], ["Target-to-clutter ratio", f"{fmt(det.get('target_clutter_ratio_db'))} dB"],
            ["Detector confidence", fmt(det.get("confidence"))], ["Box in chip (px)", fmt(det.get("bbox_pixel"))], ["Sensor / polarisation", f"{det.get('sensor')} · {det.get('polarization')}"],
            ["Scene", det.get("scene_id")], ["Position", f"{det.get('latitude'):.5f}, {det.get('longitude'):.5f}"]]
    el.append(Paragraph(f"SAR measurements {chip(d['provenance']['Radar measurements'])}", S["h2"])); el.append(kv(rows))
    el.append(Paragraph("Identity and AIS correlation", S["h2"]))
    el.append(P(rep.get("identity_attribution_summary", "")))
    gt = req.get("ground_truth") or req.get("ground_truth_ais")
    id_rows = [["Spatial discrepancy SAR↔AIS", f"{fmt(fusion.get('spatial_discrepancy_km'))} km (gate 15 km)"], ["Temporal difference", f"{fmt(fusion.get('temporal_difference_minutes'))} min (gate 60 min)"],
               ["Dimension mismatch", fmt(fusion.get("dimension_mismatch_ratio"))], ["Heading discrepancy", f"{fmt(fusion.get('heading_discrepancy_deg'))}°"],
               ["Candidate identity score", fmt(fusion.get("candidate_identity_score"))], ["Spatially correlated", fmt(fusion.get("is_spatially_correlated"))]]
    if gt:
        id_rows.append(["Ground-truth vessel (real AIS)", f"{gt.get('vessel_name')} · MMSI {gt.get('mmsi')}"])
        if gt.get("length_m") is not None:
            true_len = gt.get("length_m"); meas = det.get("length_m") or 0.0
            id_rows.append(["Measured vs true length", f"{meas:.0f} m measured vs {true_len:.0f} m reported by the vessel's own AIS (error {meas - true_len:+.0f} m)"])
    el.append(kv(id_rows))
    if req.get("chip_id"):
        el.append(P("Real-chip validation: the detector's measured length can be compared with the AIS-reported length of the ground-truth vessel (see §4 detections table).", "small"))

    # ---- 4. Imagery -----------------------------------------------------------------------------
    el.append(PageBreak()); sec("4. Imagery evidence")
    if req.get("chip_id"):
        add_img("chip", W)
        add_img("hist", 110 * mm)
    else:
        el.append(P("No raw radar chip exists for this synthetic scenario. The figure below is a schematic generated from the stated dimensions and must not be read as imagery.", "body"))
        add_img("schematic", 100 * mm)
    alld = req.get("all_detections") or [det]
    el.append(Paragraph("Detector output", S["h2"]))
    el.append(table(["Detection", "Conf.", "L (m)", "B (m)", "Hdg °", "TCR dB", "Box (px)"],
                    [[x.get("detection_id", ""), fmt(x.get("confidence")), fmt(x.get("length_m"), 0), fmt(x.get("width_m"), 0), fmt(x.get("heading_deg"), 0), fmt(x.get("target_clutter_ratio_db"), 1), fmt(x.get("bbox_pixel"))] for x in alld],
                    [52 * mm, 14 * mm, 16 * mm, 16 * mm, 16 * mm, 18 * mm, W - 132 * mm]))

    # ---- 5. AIS ----------------------------------------------------------------------------------
    el.append(PageBreak()); sec(f"5. AIS analysis {chip(d['provenance']['AIS'])}".replace("<font", "<font"))
    el.append(P(rep.get("ais_status_summary", "")))
    if ais_rec:
        el.append(kv([[k, fmt(ais_rec.get(k))] for k in ("mmsi", "vessel_name", "ship_type", "latitude", "longitude", "sog", "cog", "heading", "timestamp")]))
    else:
        el.append(P("No AIS report is associated with this detection (absent, outside the gate, or deliberately withheld).", "body"))
    gaps = req.get("historical_gaps") or []
    if gaps:
        el.append(Paragraph("Historical transmission gaps", S["h2"]))
        el.append(table(["Start", "End", "Hours", "Start pos", "Suspicious"], [[g.get("gap_start"), g.get("gap_end"), fmt(g.get("duration_hours"), 1), f"{g.get('start_lat')}, {g.get('start_lon')}", fmt(g.get("is_suspicious"))] for g in gaps], [40 * mm, 40 * mm, 16 * mm, 46 * mm, W - 142 * mm]))
        add_img("gaps", 120 * mm)
    ais_feats = [r for r in d["features"] if r["domain"] == "ais"]
    el.append(Paragraph("AIS-derived features", S["h2"]))
    el.append(table(["Feature", "Value", "Meaning"], [[r["name"], fmt(r["value"]) if r["value"] is not None else (r["note"] or "—"), r["description"]] for r in ais_feats], [48 * mm, 28 * mm, W - 76 * mm]))

    # ---- 6. Geospatial --------------------------------------------------------------------------
    el.append(PageBreak()); sec("6. Geospatial context and jurisdiction")
    el.append(P(rep.get("geospatial_eez_analysis", "")))
    add_img("map", W)
    el.append(kv([["In dataset coverage", fmt(geo.get("in_coverage"))], ["Inside EEZ", f"{fmt(geo.get('inside_eez'))} ({geo.get('eez_country') or '—'})"], ["Distance to coast", f"{fmt(geo.get('distance_to_coast_km'), 1)} km"],
                  ["Distance to EEZ boundary", f"{fmt(geo.get('distance_to_eez_boundary_km'), 1)} km"], ["Nearest port", f"{geo.get('nearest_port_name')} ({fmt(geo.get('distance_to_nearest_port_km'), 0)} km)"],
                  ["Nearest STS corridor", f"{geo.get('nearest_sts_zone_name')} ({fmt(geo.get('distance_to_sts_zone_km'), 0)} km)"], ["Risk tags", ", ".join(geo.get("risk_zone_tags") or []) or "none"]]))
    if not geo.get("in_coverage", True):
        el.append(P("The position is outside the bundled Arabian Sea dataset; distances above are to Arabian Sea features and have no bearing on this location. No jurisdiction or STS reasoning was applied.", "small"))

    # ---- 7. Sanctions ---------------------------------------------------------------------------
    el.append(PageBreak()); sec(f"7. Sanctions and registry screening {chip('REAL')}")
    el.append(P(rep.get("sanctions_findings", "")))
    el.append(kv([["Query target", sanc.get("query_target")], ["Result", f"{'SANCTIONED' if sanc.get('is_sanctioned') else 'no match'} — risk {sanc.get('overall_sanctions_risk')}"], ["Sources screened", ", ".join(sanc.get("screened_sources") or [])], ["Notes", sanc.get("screening_notes") or "—"]]))
    matches = sanc.get("matches") or []
    if matches:
        el.append(table(["List", "Entity", "IMO / MMSI", "Programmes", "Score", "Basis"], [[m.get("source_list"), m.get("entity_name"), f"{m.get('matched_imo') or '—'} / {m.get('matched_mmsi') or '—'}", ", ".join(m.get("sanction_programs") or []), fmt(m.get("match_score")), m.get("match_basis")] for m in matches], [22 * mm, 40 * mm, 34 * mm, 38 * mm, 12 * mm, W - 146 * mm]))
    inv = {a["id"]: a for a in (d["inventory"].get("assets") or [])}
    el.append(P("Registries: " + "; ".join(f"{inv[k]['name']} (file SHA-256 {str(inv[k].get('sha256'))[:12]}…)" for k in ("sdn.xml", "un_consolidated.xml") if k in inv), "small"))

    # ---- 8. Features ----------------------------------------------------------------------------
    el.append(PageBreak()); sec("8. Feature appendix (all engineered features)")
    for domain in ("sar", "ais", "geospatial", "historical", "fusion"):
        rows = [r for r in d["features"] if r["domain"] == domain]
        el.append(Paragraph(f"{domain.upper()} {chip(rows[0]['provenance'])}", S["h2"]))
        el.append(table(["Feature", "Value", "Definition / formula"], [[r["name"], fmt(r["value"]) if r["value"] is not None else (r["note"] or "—"), r["description"] + (f"  [{r['formula']}]" if r["formula"] else "")] for r in rows], [46 * mm, 26 * mm, W - 72 * mm]))

    # ---- 9. Risk --------------------------------------------------------------------------------
    el.append(PageBreak()); sec(f"9. Risk assessment {chip('HEURISTIC')}")
    el.append(kv([["Classification", risk.get("dark_vessel_classification")], ["Dark-vessel probability", fmt(risk.get("dark_vessel_probability"))], ["Sanctions risk", risk.get("sanctions_risk_level")], ["EEZ threat", risk.get("eez_threat_level")],
                  ["Overall anomaly score", f"{fmt(risk.get('overall_anomaly_score'))}  = 0.60·p + (0.30 if sanctioned else 0.05) + (0.10 if inside EEZ)"], ["Threat tier", f"{tier}  (SEVERE ≥ 0.80 or sanctioned; HIGH ≥ 0.60 or dark-evasion; MEDIUM ≥ 0.35 or shadow-zone)"]]))
    el.append(Paragraph("Risk factors that fired", S["h2"]))
    for f_ in risk.get("risk_factors") or ["(none)"]:
        el.append(Paragraph(esc(f_), S["bullet"], bulletText="•"))
    el.append(Paragraph("Scoring rules (deterministic)", S["h2"]))
    el.append(table(["Rule", "Effect on p"], [["Prior for an unmatched radar target", "0.50"], ["Length < 30 m (and < 30 km from coast → exempt class)", "−0.35"], ["Length ≥ 100 m (AIS mandatory under SOLAS V/19)", "+0.30"], ["> 100 km from coast (only when position is within dataset coverage)", "+0.15"],
                                        ["Within 80 km of an STS corridor (coverage required)", "+0.15"], ["Active AIS gap ≥ 12 h", "+0.10"], ["Sensor blackout / shadow-zone note", "capped to 0.40–0.65"], ["Correlated with AIS", "p = 0.05, CORRELATED_BENIGN"],
                                        ["p ≥ 0.70 → DELIBERATE_DARK_EVASION; ≥ 0.40 → AIS_SHADOW_ZONE", "classification"]], [W * 0.75, W * 0.25]))
    if d["counterfactuals"]:
        el.append(Paragraph("Counterfactual re-scoring", S["h2"]))
        el.append(P("Each row re-runs the production scorer with one input changed; it shows how fragile or robust the assessment is.", "small"))
        add_img("cf", 140 * mm)
        el.append(table(["Scenario", "p", "Classification", "Change"], [[r["label"], fmt(r["probability"]), r["classification"], r["change"]] for r in d["counterfactuals"]], [52 * mm, 14 * mm, 50 * mm, W - 116 * mm]))
        add_img("sens", 120 * mm)

    # ---- 10. Forecast ---------------------------------------------------------------------------
    el.append(PageBreak()); sec(f"10. Predictive forecast {chip('DERIVED')}")
    wps = forecast.get("extrapolated_waypoints") or []
    el.append(table(["Horizon", "Latitude", "Longitude", "Uncertainty radius", "Time (UTC)"], [[f"+{w.get('projection_hours'):g} h", fmt(w.get("projected_lat"), 4), fmt(w.get("projected_lon"), 4), f"±{fmt(w.get('uncertainty_radius_km'), 1)} km", w.get("projected_timestamp")] for w in wps], [20 * mm, 26 * mm, 26 * mm, 34 * mm, W - 106 * mm]))
    el.append(kv([["Forecast confidence", fmt(forecast.get("forecast_confidence"))], ["Methodology", forecast.get("methodology_notes") or "Dead-reckoning from last speed/heading with expanding drift cones."], ["Predicted EEZ incursion", fmt(forecast.get("projected_eez_incursion"))], ["Predicted activity", forecast.get("projected_activity") or "—"]]))
    if not ais_rec:
        el.append(P("No AIS speed/course exists for this target, so the forecast uses a default assumed speed along the radar-estimated heading (itself coarse). Treat the cones as illustrative.", "small"))
    el.append(P("Dead reckoning assumes constant speed and heading; it is not a prediction of intent.", "small"))

    # ---- 11. Trace ------------------------------------------------------------------------------
    el.append(PageBreak()); sec("11. Agent workflow trace")
    add_img("flow", W)
    tr = ctx.get("execution_trace") or []
    el.append(table(["#", "Node", "Status", "ms", "Action", "Notes"], [[t.get("step_number"), t.get("agent_name"), t.get("status"), fmt(t.get("latency_ms"), 1) if t.get("latency_ms") is not None else "—", t.get("action_taken"), t.get("notes") or ""] for t in tr], [8 * mm, 34 * mm, 22 * mm, 12 * mm, 40 * mm, W - 116 * mm]))
    add_img("lat", 110 * mm)
    el.append(Paragraph("Degradation notes", S["h2"]))
    for n in ctx.get("degradation_notes") or ["None — all evidence sources were available."]:
        el.append(Paragraph(esc(n), S["bullet"], bulletText="•"))

    # ---- 12. HITL -------------------------------------------------------------------------------
    sec("12. Human review")
    el.append(P("A human checkpoint was " + ("required by the risk gate (high risk or sanctions)." if ctx.get("human_in_the_loop_required") else "not required for this case.")))
    dec = ctx.get("hitl_decisions") or []
    if dec:
        el.append(table(["Time (UTC)", "Disposition", "Operator notes"], [[x.get("timestamp"), x.get("disposition"), x.get("notes")] for x in dec], [42 * mm, 30 * mm, W - 72 * mm]))
    elif ctx.get("human_in_the_loop_required"):
        el.append(P("No analyst decision had been recorded when this report was exported.", "body"))
    lc = d["ledger_check"]
    el.append(P(f"Audit ledger: {lc['length']} entries · hash chain {'VERIFIED' if lc['valid'] else 'BROKEN at entry ' + str(lc['broken_at'])} · head {str(lc['head'])[:16]}…", "small"))
    if d["case_ledger"]:
        el.append(table(["#", "Time", "Action", "Operator", "Hash"], [[e["index"], e["timestamp"], e["action"], e["operator"], e["hash"][:14] + "…"] for e in d["case_ledger"]], [8 * mm, 46 * mm, 52 * mm, 30 * mm, W - 136 * mm]))

    # ---- 13. Legal ------------------------------------------------------------------------------
    el.append(PageBreak()); sec("13. Legal basis")
    el.append(P("Statutory text is taken from a fixed catalogue — it is never produced by a language model.", "small"))
    for l in d["legal"]:
        el.append(KeepTogether([Paragraph(f"{esc(l['title'])}  {'— CITED' if l['triggered'] else '— not cited'}", S["h2"]), P(l["statute"]), P(M(f"<b>Why:</b> {esc(l['why'])}")), P(l["link"] or "", "small")]))

    # ---- 14. Alternatives & limits --------------------------------------------------------------
    el.append(PageBreak()); sec("14. Alternative hypotheses, confidence and limitations")
    for h in d["hypotheses"]:
        el.append(KeepTogether([Paragraph(f"{esc(h['name'])}  ·  weight: {h['weight']}", S["h2"]),
                                P(M("<b>Supports:</b> " + esc("; ".join(h["for"]) or "—"))), P(M("<b>Against:</b> " + esc("; ".join(h["against"]) or "—"))), P(M("<b>Would settle it:</b> " + esc(h["settle"])))]))
    el.append(Paragraph("Confidence statement", S["h2"])); el.append(P(rep.get("analyst_confidence_statement", "")))
    el.append(Paragraph("Limitations of this assessment", S["h2"]))
    for it in d["limitations"]:
        el.append(Paragraph(esc(it), S["bullet"], bulletText="•"))

    # ---- 15. Lineage ----------------------------------------------------------------------------
    el.append(PageBreak()); sec("15. Data lineage and provenance")
    el.append(table(["Input", "Provenance"], [[k, Paragraph(chip(v), S["cell"])] for k, v in d["provenance"].items()], [W * 0.6, W * 0.4]))
    if req.get("provenance", {}).get("source"):
        el.append(P(f"Source of this case: {req['provenance']['source']}", "small"))
    el.append(Paragraph("Platform data inventory", S["h2"]))
    el.append(table(["Asset", "Provenance", "Count", "Source / details"], [[a["name"], Paragraph(chip(a["provenance"]), S["cell"]), fmt(a.get("count")), f"{a.get('source', '')} {a.get('details', '')}".strip()] for a in d["inventory"].get("assets", [])], [50 * mm, 24 * mm, 16 * mm, W - 90 * mm]))

    # ---- 16. Integrity --------------------------------------------------------------------------
    el.append(PageBreak()); sec("16. Integrity and reproducibility")
    el.append(kv([["Evidence SHA-256", Paragraph(f'<font name="{FM}" size="6.5">{d["evidence_hash"]}</font>', S["cell"])], ["Audit chain head", str(lc["head"])], ["Software versions", json.dumps(d["versions"])],
                  ["Narrative producer", narrative.get("label", "")]]))
    trimmed = {k: v for k, v in req.items() if k not in ("all_detections", "ground_truth_ais")}
    el.append(Paragraph("Request that produced this report", S["h2"]))
    el.append(Paragraph(esc(json.dumps(trimmed, indent=1, default=str)[:3500]).replace("\n", "<br/>").replace(" ", "&nbsp;"), S["mono"]))
    el.append(Paragraph("Reproduce", S["h2"]))
    el.append(Paragraph("POST /api/investigate with the JSON above; deterministic stages (features, scoring, forecast, sanctions) return identical values for identical inputs.", S["body"]))

    # ---- Appendix -------------------------------------------------------------------------------
    el.append(PageBreak()); sec("Appendix A. Glossary")
    gl = [("SAR", "Synthetic Aperture Radar — active microwave imaging that works day and night through cloud."), ("AIS", "Automatic Identification System — ship transponder broadcasts (position, speed, identity)."),
          ("EEZ", "Exclusive Economic Zone — up to 200 nautical miles from a coast (UNCLOS)."), ("STS", "Ship-to-ship transfer of cargo at sea."), ("TCR", "Target-to-clutter ratio: target backscatter minus local sea clutter (dB)."),
          ("HITL", "Human-in-the-loop — a mandatory analyst decision point."), ("Provenance", "REAL (observed data), DERIVED (computed from real data), SYNTHETIC (generated test data), HEURISTIC (rule-based judgement), UNAVAILABLE (missing).")]
    el.append(table(["Term", "Meaning"], [[a, b] for a, b in gl], [28 * mm, W - 28 * mm]))

    doc.multiBuild(el)
    return buf.getvalue()
