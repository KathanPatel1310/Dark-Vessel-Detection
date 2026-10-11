"""reportlab renderer for the incident brief.

Design: US Letter, white page, near-black navy ink, one vermilion accent used only for the verdict and
flags. Serif headings (Instrument Serif), sans body (Inter), monospace labels (JetBrains Mono). Hairline
rules instead of filled tables; each finding carries a status tag and a "what it does / what it tells you"
pair. Fonts are bundled in src/reporting/fonts (SIL Open Font License).
"""

import io
import json
import os
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Frame, Image, KeepTogether, PageBreak, PageTemplate, Paragraph, Spacer, Table,
                                TableStyle)

_FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
_FONTS = {"IN": "Inter-Regular.ttf", "IN-M": "Inter-Medium.ttf", "IN-SB": "Inter-SemiBold.ttf", "MO": "JetBrainsMono-Regular.ttf",
          "MO-M": "JetBrainsMono-Medium.ttf", "SE": "InstrumentSerif-Regular.ttf", "SE-I": "InstrumentSerif-Italic.ttf"}
_OK = all(os.path.exists(os.path.join(_FONT_DIR, f)) for f in _FONTS.values())
if _OK:
    for _n, _f in _FONTS.items():
        pdfmetrics.registerFont(TTFont(_n, os.path.join(_FONT_DIR, _f)))
    pdfmetrics.registerFontFamily("IN", normal="IN", bold="IN-SB", italic="IN", boldItalic="IN-SB")
    pdfmetrics.registerFontFamily("SE", normal="SE", bold="SE", italic="SE-I", boldItalic="SE-I")
    SANS, SANS_M, SANS_B, MONO, MONO_M, SERIF, SERIF_I = "IN", "IN-M", "IN-SB", "MO", "MO-M", "SE", "SE-I"
else:  # fonts missing: built-ins keep generation working
    SANS = SANS_M = SANS_B = "Helvetica"
    MONO = MONO_M = "Courier"
    SERIF = SERIF_I = "Times-Roman"

INK = colors.HexColor("#0F1B2D")
MUTED = colors.HexColor("#6B7785")
RULE = colors.HexColor("#C9D1D9")
HAIR = colors.HexColor("#E1E6EB")
ACCENT = colors.HexColor("#D9431E")
ACCENT_HEX = "#D9431E"
MUTED_HEX = "#6B7785"

PAGE_W, PAGE_H = LETTER
ML = MR = 0.95 * inch
W = PAGE_W - ML - MR

_REPLACE = {"≥": ">=", "≤": "<=", "→": "to", "↔": "to", "≈": "~", "Δ": "delta", "✓": "yes", "π": "pi", "θ": "theta", "Σ": "sum", "σ": "sigma", "λ": "lambda", "µ": "u"}


def clean(x: Any) -> str:
    s = "" if x is None else str(x)
    for a, b in _REPLACE.items():
        s = s.replace(a, b)
    return s


def esc(x: Any) -> str:
    return clean(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class M(str):
    """Marks a string as reportlab markup (everything else is escaped)."""


def _cell(x: Any) -> str:
    return str(x) if isinstance(x, M) else esc(x)


S = {
    "title": ParagraphStyle("title", fontName=SERIF, fontSize=34, leading=38, textColor=INK, spaceAfter=10),
    "h2": ParagraphStyle("h2", fontName=SERIF, fontSize=17, leading=21, textColor=INK),
    "h3": ParagraphStyle("h3", fontName=SERIF, fontSize=13.5, leading=17, textColor=INK, spaceBefore=6, spaceAfter=3),
    "lead": ParagraphStyle("lead", fontName=SERIF, fontSize=15, leading=20.5, textColor=INK, spaceAfter=6),
    "body": ParagraphStyle("body", fontName=SANS, fontSize=9.4, leading=14.2, textColor=INK, spaceAfter=5, alignment=TA_LEFT),
    "small": ParagraphStyle("small", fontName=SANS, fontSize=8, leading=11.6, textColor=MUTED, spaceAfter=3),
    "label": ParagraphStyle("label", fontName=MONO, fontSize=6.8, leading=9, textColor=MUTED),
    "cell": ParagraphStyle("cell", fontName=SANS, fontSize=8.4, leading=11.8, textColor=INK),
    "cellh": ParagraphStyle("cellh", fontName=SANS, fontSize=8.2, leading=11, textColor=MUTED),
    "mono": ParagraphStyle("mono", fontName=MONO, fontSize=7.2, leading=10.2, textColor=INK),
    "bullet": ParagraphStyle("bullet", fontName=SANS, fontSize=9.2, leading=13.6, leftIndent=14, firstLineIndent=-14, textColor=INK, spaceAfter=2),
    "key": ParagraphStyle("key", fontName=SANS, fontSize=8.5, leading=12, textColor=MUTED),
    "val": ParagraphStyle("val", fontName=SANS_M, fontSize=9.2, leading=12, textColor=INK),
    "big": ParagraphStyle("big", fontName=SERIF, fontSize=30, leading=33, textColor=INK),
    "bigcap": ParagraphStyle("bigcap", fontName=SANS, fontSize=7.8, leading=10.5, textColor=MUTED),
    "tag": ParagraphStyle("tag", fontName=MONO, fontSize=6.8, leading=8.5, textColor=INK),
}


def P(text: Any, style: str = "body") -> Paragraph:
    return Paragraph(_cell(text), S[style])


def fmt(v: Any, nd: int = 2) -> str:
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, float):
        return f"{v:.{nd}f}"
    return str(v)


def img(png: Optional[bytes], width: float) -> Optional[Image]:
    if not png:
        return None
    iw, ih = ImageReader(io.BytesIO(png)).getSize()
    return Image(io.BytesIO(png), width=width, height=width * ih / iw)


def tagbox(text: str) -> Table:
    t = clean(text).upper()
    w = stringWidth(t, MONO, 6.8) + 12
    box = Table([[Paragraph(esc(t), S["tag"])]], colWidths=[w])
    box.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, INK), ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                             ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]))
    return box


def section(title: str, tag: Optional[str] = None, rule: bool = True, need: float = 1.6) -> List[Any]:
    cells = [Paragraph(esc(title), S["h2"]), tagbox(tag) if tag else ""]
    tw = (stringWidth(clean(tag).upper(), MONO, 6.8) + 12) if tag else 1
    row = Table([cells], colWidths=[W - tw - 4, tw + 4])
    style = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (1, 0), (1, 0), "RIGHT"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
             ("TOPPADDING", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]
    if rule:
        style.append(("LINEABOVE", (0, 0), (-1, 0), 0.5, RULE))
    row.setStyle(TableStyle(style))
    return [CondPageBreak(need * inch), row]


def two_col(does: str, tells: str) -> Table:
    t = Table([[Paragraph("WHAT IT DOES", S["label"]), "", Paragraph("WHAT IT TELLS YOU", S["label"])],
               [Paragraph(esc(does), S["cell"]), "", Paragraph(esc(tells), S["cell"])]], colWidths=[W / 2 - 10, 20, W / 2 - 10])
    t.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, 0), 0.4, HAIR), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, 0), 7), ("BOTTOMPADDING", (0, 0), (-1, 0), 3), ("BOTTOMPADDING", (0, 1), (-1, 1), 6)]))
    return KeepTogether([t])


def method(text: str) -> Paragraph:
    return Paragraph(f'<font name="{MONO}" size="6.6" color="{MUTED_HEX}">METHOD</font>&nbsp;&nbsp;{esc(text)}', S["small"])


def ledger(header: List[str], rows: List[List[Any]], widths: List[float], mono_cols: Optional[List[int]] = None) -> Table:
    mono_cols = mono_cols or []
    data = [[Paragraph(esc(h), S["cellh"]) for h in header]]
    for r in rows:
        data.append([c if hasattr(c, "wrap") else Paragraph(_cell(c), S["mono"] if i in mono_cols else S["cell"]) for i, c in enumerate(r)])
    t = Table(data, colWidths=widths, repeatRows=1)
    st = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, 0), 0.6, INK), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
          ("TOPPADDING", (0, 0), (-1, -1), 4.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5)]
    st += [("LINEBELOW", (0, i), (-1, i), 0.3, HAIR) for i in range(1, len(data))]
    t.setStyle(TableStyle(st))
    return t


def meta_grid(pairs: List[tuple]) -> Table:
    rows = []
    for i in range(0, len(pairs), 2):
        a = pairs[i]
        b = pairs[i + 1] if i + 1 < len(pairs) else ("", "")
        rows.append([Paragraph(esc(a[0]), S["key"]), Paragraph(_cell(a[1]), S["val"]), Paragraph(esc(b[0]), S["key"]), Paragraph(_cell(b[1]), S["val"])])
    t = Table(rows, colWidths=[W * 0.16, W * 0.34, W * 0.16, W * 0.34])
    t.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, 0), 0.6, INK)] + [("LINEBELOW", (0, i), (-1, i), 0.3, RULE) for i in range(len(rows))] +
                           [("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    return t


def stat_strip(cells: List[tuple]) -> Table:
    n = len(cells)
    data = [[[Paragraph(esc(big), S["big"]), Spacer(1, 2), Paragraph(esc(cap), S["bigcap"])] for big, cap in cells]]
    t = Table(data, colWidths=[W / n] * n)
    t.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, 0), 0.6, INK), ("LINEBELOW", (0, 0), (-1, 0), 0.4, RULE)] + [("LINEAFTER", (i, 0), (i, 0), 0.4, RULE) for i in range(n - 1)] +
                           [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("LEFTPADDING", (1, 0), (-1, -1), 12), ("TOPPADDING", (0, 0), (-1, -1), 12), ("BOTTOMPADDING", (0, 0), (-1, -1), 12)]))
    return t


def statline(items: List[tuple]) -> Paragraph:
    parts = "&nbsp;&nbsp;&nbsp;&nbsp;".join(f'<font name="{SANS}" color="{MUTED_HEX}">{esc(k)}</font>&nbsp;<font name="{MONO_M}">{esc(v)}</font>' for k, v in items)
    return Paragraph(parts, S["small"])


def bullets(items: List[str], mark: str = "—") -> List[Any]:
    return [Paragraph(f"{mark}&nbsp;&nbsp;{esc(i)}", S["bullet"]) for i in items]


def make_canvas(meta: Dict[str, str]):
    class NumberedCanvas(rl_canvas.Canvas):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            self._saved: List[dict] = []

        def showPage(self):
            self._saved.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._saved)
            for state in self._saved:
                self.__dict__.update(state)
                self._chrome(total)
                super().showPage()
            super().save()

        def _chrome(self, total: int):
            self.saveState()
            top = PAGE_H - 0.55 * inch
            # mark: underscore plus two dots, echoing a prompt glyph
            self.setStrokeColor(INK)
            self.setLineWidth(0.9)
            self.line(ML, top - 1, ML + 7, top - 1)
            self.setFillColor(INK)
            self.circle(ML + 11, top + 4.5, 0.9, stroke=0, fill=1)
            self.circle(ML + 11, top - 1, 0.9, stroke=0, fill=1)
            self.setFont(SANS_M, 8.4)
            self.drawString(ML + 19, top - 2, "DVD-MDA incident brief")
            self.setFont(MONO, 7.6)
            self.drawRightString(PAGE_W - MR, top - 2, meta["header_right"])
            self.setStrokeColor(RULE)
            self.setLineWidth(0.5)
            self.line(ML, top - 11, PAGE_W - MR, top - 11)
            self.line(ML, 0.62 * inch, PAGE_W - MR, 0.62 * inch)
            self.setFont(MONO, 7.4)
            self.setFillColor(MUTED)
            self.drawString(ML, 0.45 * inch, meta["footer_left"])
            self.drawRightString(PAGE_W - MR, 0.45 * inch, f"Page {self._pageNumber} of {total}")
            self.restoreState()

    return NumberedCanvas


def render(d: Dict[str, Any], narrative: Dict[str, Any], figs: Dict[str, Optional[bytes]]) -> bytes:
    ctx = d["ctx"]
    rep = ctx.get("report") or {}
    det = ctx.get("detection") or {}
    risk = ctx.get("risk_assessment") or {}
    geo = ctx.get("geo_context") or {}
    sanc = ctx.get("sanctions") or {}
    feats = ctx.get("features") or {}
    fusion = feats.get("fusion") or {}
    ais_rec = ctx.get("ais_used")
    forecast = ctx.get("forecast") or {}
    req = ctx.get("request") or {}
    v = d["verdict"]
    tier = v["tier"]
    prob = risk.get("dark_vessel_probability")
    corr = bool(fusion.get("is_spatially_correlated"))
    is_real = bool(req.get("chip_id"))
    withheld = bool(req.get("simulate_ais_offline"))
    case_id = req.get("scenario_id") or req.get("chip_id") or ctx.get("mission_id")
    report_id = rep.get("report_id", ctx.get("mission_id"))
    short_id = str(d["evidence_hash"])[:8]

    meta = {"header_right": str(case_id)[:40], "footer_left": f"Report {report_id} · {short_id}"}
    buf = io.BytesIO()
    doc = BaseDocTemplate(buf, pagesize=LETTER, leftMargin=ML, rightMargin=MR, topMargin=0.95 * inch, bottomMargin=0.85 * inch,
                          title=f"Incident brief {report_id}", author="DVD-MDA", subject="Maritime incident brief")
    frame = Frame(ML, 0.85 * inch, W, PAGE_H - 0.95 * inch - 0.85 * inch, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0, id="f")
    doc.addPageTemplates([PageTemplate(id="p", frames=[frame])])
    el: List[Any] = []

    def fig(key: str, width: float = W) -> None:
        im = img(figs.get(key), width)
        if im is not None:
            el.append(im)
            el.append(Spacer(1, 5))

    data_label = ("Real Sentinel-1 chip" + (", AIS withheld as a test" if withheld else ", real AIS")) if is_real else "Synthetic benchmark scenario"
    L = det.get("length_m") or 0.0

    # Plain-language lead sentence, written by code from the evidence
    if corr and sanc.get("is_sanctioned"):
        progs = ", ".join(sorted({p for m in (sanc.get("matches") or []) for p in (m.get("sanction_programs") or [])})) or "a listed programme"
        lead = (f"{v['subject']} matched an AIS broadcast, so the radar target is explained, but its identifiers match a sanctions registry entry ({progs}). "
                f"That match alone sets the threat tier to {tier}.")
    elif corr:
        lead = f"{v['subject']} matched an AIS broadcast, so the radar target is explained. The threat tier is {tier}."
    else:
        lead = (f"A {L:.0f} m radar target at ({det.get('latitude', 0):.2f}, {det.get('longitude', 0):.2f}) has no matching AIS broadcast. "
                f"The rule-based score is {fmt(prob)} against a dark-evasion line of 0.70, giving threat tier {tier}.")
        if sanc.get("is_sanctioned"):
            lead += " A sanctions registry entry also matched."

    # ============ Page 1 =========================================================================
    el.append(Spacer(1, 8))
    el.append(Paragraph(f'{esc(v["subject"])}: <font color="{ACCENT_HEX}">{esc(v["phrase"])}</font>', S["title"]))
    el.append(meta_grid([
        ("Case", case_id), ("Flagged (UTC)", str(ctx.get("created_at", ""))[:16].replace("T", " ")),
        ("Threat tier", tier), ("Position", f"{det.get('latitude', 0):.4f}, {det.get('longitude', 0):.4f}"),
        ("Hypothesis", f"{prob:.2f} dark-vessel probability" if prob is not None else "—"), ("Data", data_label),
        ("Decided by", "the rule-based risk scorer"), ("Human review", "required" if ctx.get("human_in_the_loop_required") else "not required"),
        ("Target", str(det.get("detection_id", ""))[4:] if str(det.get("detection_id", "")).startswith("SAR-") else det.get("detection_id", "")), ("Mission", ctx.get("mission_id")),
    ]))
    el.append(Spacer(1, 12))
    el.append(Paragraph(esc(lead), S["lead"]))
    if narrative.get("generated_by") == "LLM_VERIFIED":
        el.append(P(M(f'<font name="{MONO}" size="6.6" color="{MUTED_HEX}">AI SUMMARY</font>&nbsp;&nbsp;{esc(narrative["paragraphs"][0])}'), "small"))
        el.append(P("Drafted by the fine-tuned Qwen 2.5 model, then checked against the stored evidence: every number, tier, classification and jurisdiction matched.", "small"))
    else:
        el.append(P("Written by the report engine from the stored evidence. No language model was used for this text.", "small"))
    map_im = img(figs.get("map"), W)
    if map_im is not None:
        el.append(KeepTogether([Spacer(1, 6), Paragraph("Position", S["h3"]), map_im, Spacer(1, 4),
                                P("Solid marker: radar detection. Triangle: AIS position, if any. Dashed line and hatched circles: dead-reckoning track with growing uncertainty. Dotted ellipses: ship-to-ship corridors.", "small")]))

    # ============ Decision =======================================================================
    el.append(PageBreak())
    el += section("Decision", f"Threat tier: {tier}", rule=False)
    detail = (narrative.get("rule_based_paragraphs") or narrative.get("paragraphs") or [lead])
    for p in detail:
        el.append(P(p))
    el.append(Spacer(1, 4))
    el.append(stat_strip([(fmt(prob), "Dark-vessel probability (higher means more suspicious)"), (fmt(risk.get("overall_anomaly_score")), "Anomaly score: 0.60 × probability, plus sanctions and EEZ terms"),
                          (str(risk.get("dark_vessel_classification", "—")).replace("_", " ").lower(), "Classification")]))
    el.append(Spacer(1, 8))
    el.append(P("Each bar shows the running probability after one rule. The dashed line is 0.70, where an unmatched target is called a deliberate dark-vessel case.", "small"))
    fig("score", W)
    el.append(two_col("Starts from a neutral prior for a radar target with no AIS match, then adds or subtracts fixed amounts for hull size, distance offshore, ship-to-ship corridor proximity and how long AIS has been silent.",
                      "How strongly the evidence points to AIS being off on purpose. It is a rule-based judgement with documented thresholds, not a calibrated probability, so treat the number as a ranking aid."))
    el.append(method("src/analytics/risk_scorer.py · reports/risk_scorer_validation.md"))
    if d["counterfactuals"]:
        el += section("What if the evidence were different?", "Context", need=3.6)
        el.append(P("Each row re-runs the production scorer with one input changed. It shows how fragile or robust the call is.", "body"))
        row = Table([[img(figs.get("cf"), W * 0.52) or "", img(figs.get("sens"), W * 0.44) or ""]], colWidths=[W * 0.55, W * 0.45])
        row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
        el.append(row)
        el.append(Spacer(1, 4))
        el.append(ledger(["Scenario", "Probability", "Classification", "Input changed"],
                         [[r["label"], fmt(r["probability"]), r["classification"].replace("_", " ").lower(), r["change"]] for r in d["counterfactuals"]],
                         [W * 0.30, W * 0.12, W * 0.28, W * 0.30], mono_cols=[3]))

    # ============ Radar ==========================================================================
    el += section("Radar detection", "Weak" if (det.get("confidence") or 0) < 0.8 else "Context", need=4.2)
    tcr = det.get("target_clutter_ratio_db")
    contrast = f", standing {tcr:.1f} dB above the surrounding sea" if tcr else ""
    el.append(P(f"The detector found a ship-sized target about {L:.0f} m long and {det.get('width_m') or 0:.0f} m wide, with confidence {det.get('confidence') or 0:.2f}{contrast}."))
    if is_real:
        fig("chip", W)
        fig("hist", W * 0.5)
    else:
        el.append(P("This is a synthetic scenario, so there is no radar image. The sketch below is drawn from the stated dimensions only.", "small"))
        fig("schematic", W * 0.5)
    gt = req.get("ground_truth")
    stats = [("Length", f"{L:.0f} m"), ("Beam", f"{det.get('width_m') or 0:.0f} m"), ("Confidence", fmt(det.get("confidence"))), ("Contrast", f"{fmt(det.get('target_clutter_ratio_db'), 1)} dB" if det.get("target_clutter_ratio_db") else "not measured")]
    if gt and gt.get("length_m") is not None:
        stats.append(("Vessel's own AIS length", f"{gt['length_m']:.0f} m (error {L - gt['length_m']:+.0f} m)"))
    el.append(statline(stats))
    el.append(two_col("A neural detector finds ships in the dual-polarisation radar image. Length and beam come from the size of the detected box at 10 m per pixel; contrast comes from comparing the target with a 15-pixel ring of sea around it.",
                      "That something ship-sized was at this place and time, whatever its transponder says. Size is good to about 10 m, and the heading read from the box is coarse."))
    alld = req.get("all_detections") or [det]
    if len(alld) > 1:
        el.append(Spacer(1, 4))
        el.append(ledger(["Detection", "Confidence", "Length", "Beam", "Contrast"],
                         [[x.get("detection_id", "")[-26:], fmt(x.get("confidence")), f"{x.get('length_m', 0):.0f} m", f"{x.get('width_m', 0):.0f} m", f"{fmt(x.get('target_clutter_ratio_db'), 1)} dB"] for x in alld],
                         [W * 0.42, W * 0.14, W * 0.14, W * 0.14, W * 0.16], mono_cols=[0]))
    el.append(method("src/models/sar_detector.py · reports/feature_math_validation.md"))

    # ============ AIS ============================================================================
    el += section("AIS correlation", "Normal" if corr else "Fired", need=3.2)
    el.append(P(rep.get("ais_status_summary", "")))
    na = "n/a: no AIS candidate"
    rows = [["Distance, radar to AIS", na if not ais_rec else f"{fmt(fusion.get('spatial_discrepancy_km'))} km (gate 15 km)"],
            ["Time difference", na if not ais_rec else f"{fmt(fusion.get('temporal_difference_minutes'))} min (gate 60 min)"],
            ["Length mismatch", fmt(fusion.get("dimension_mismatch_ratio"))],
            ["Heading difference", f"{fmt(fusion.get('heading_discrepancy_deg'))}°" if fusion.get("heading_discrepancy_deg") is not None else "—"],
            ["Identity score", na if not ais_rec else fmt(fusion.get("candidate_identity_score"))]]
    if ais_rec:
        rows = [["Vessel", f"{ais_rec.get('vessel_name') or '—'} · MMSI {ais_rec.get('mmsi')}"], ["Reported speed and course", f"{fmt(ais_rec.get('sog'), 1)} kn · {fmt(ais_rec.get('cog'), 0)}°"]] + rows
    el.append(ledger(["Measure", "Value"], rows, [W * 0.38, W * 0.62]))
    gaps = req.get("historical_gaps") or []
    if gaps:
        el.append(Spacer(1, 6))
        fig("gaps", W * 0.55)
        el.append(ledger(["Gap starts", "Hours silent", "Where", "Flagged"],
                         [[g.get("gap_start"), fmt(g.get("duration_hours"), 1), f"{g.get('start_lat')}, {g.get('start_lon')}", "yes" if g.get("is_suspicious") else "no"] for g in gaps],
                         [W * 0.30, W * 0.18, W * 0.34, W * 0.18], mono_cols=[0, 2]))
    el.append(two_col("Looks for an AIS broadcast within 15 km and 60 minutes of the radar position, then compares distance, time, length and heading between the two.",
                      "A match explains the radar target as an ordinary transmitting ship. No match means only that no transmitter was found: the vessel may be exempt, outside receiver coverage, or hiding."))
    el.append(method("src/agents/tools.py, correlate_sar_ais"))

    # ============ Jurisdiction ===================================================================
    el += section("Position and jurisdiction", "Context" if geo.get("in_coverage", True) else "Could not check", need=3.0)
    el.append(P(rep.get("geospatial_eez_analysis", "")))
    if geo.get("in_coverage", True):
        el.append(ledger(["Measure", "Value"], [
            ["Inside an EEZ", f"{fmt(geo.get('inside_eez'))} ({geo.get('eez_country') or 'international waters'})"],
            ["Distance to coast", f"{fmt(geo.get('distance_to_coast_km'), 0)} km"], ["Distance to EEZ boundary", f"{fmt(geo.get('distance_to_eez_boundary_km'), 0)} km"],
            ["Nearest port", f"{geo.get('nearest_port_name')} ({fmt(geo.get('distance_to_nearest_port_km'), 0)} km)"],
            ["Nearest ship-to-ship corridor", f"{geo.get('nearest_sts_zone_name')} ({fmt(geo.get('distance_to_sts_zone_km'), 0)} km)"]], [W * 0.38, W * 0.62]))
    else:
        el.append(P("The bundled zone and corridor data cover the Arabian Sea only. Distances for this position would be measured to features thousands of kilometres away, so none are reported and the score ignores them."))
    el.append(two_col("Places the position against the bundled maritime zones and corridors, and measures distance to coast, EEZ boundary, port and ship-to-ship transfer corridor.",
                      "Which state's rules apply, and whether the position fits a known transfer pattern. Outside the dataset it says nothing at all."))
    el.append(method("src/geospatial/eez_checker.py"))

    # ============ Sanctions ======================================================================
    el += section("Sanctions screening", "Fired" if sanc.get("is_sanctioned") else "Normal", need=2.6)
    el.append(P(rep.get("sanctions_findings", "")))
    matches = sanc.get("matches") or []
    if matches:
        el.append(ledger(["List", "Entity", "IMO / MMSI", "Programme", "Score"],
                         [[m.get("source_list"), m.get("entity_name"), f"{m.get('matched_imo') or '—'} / {m.get('matched_mmsi') or '—'}", ", ".join(m.get("sanction_programs") or []), fmt(m.get("match_score"))] for m in matches],
                         [W * 0.16, W * 0.26, W * 0.26, W * 0.22, W * 0.10], mono_cols=[2]))
    el.append(two_col("Compares the identifiers available (IMO, MMSI, name) against the OFAC SDN and UN consolidated lists, loaded from the official files.",
                      "A hit is a lead for the registry owner, not proof of identity. With no identifier, as for an unmatched radar target, the screen cannot say anything."))
    el.append(method("src/data/sanctions_parser.py · list file hashes in the appendix"))

    # ============ Forecast =======================================================================
    wps = forecast.get("extrapolated_waypoints") or []
    el += section("Forecast", "Context", need=3.0)
    el.append(ledger(["Horizon", "Latitude", "Longitude", "Uncertainty", "Time (UTC)"],
                     [[f"+{w.get('projection_hours'):g} h", fmt(w.get("projected_lat"), 3), fmt(w.get("projected_lon"), 3), f"±{fmt(w.get('uncertainty_radius_km'), 1)} km", str(w.get("projected_timestamp"))[:16].replace("T", " ")] for w in wps],
                     [W * 0.14, W * 0.18, W * 0.18, W * 0.22, W * 0.28], mono_cols=[1, 2, 4]))
    el.append(Spacer(1, 4))
    note = forecast.get("methodology_notes") or "Dead reckoning from the last speed and heading, with a circle of uncertainty that grows with time."
    if not ais_rec:
        note += " No AIS speed exists for this target, so a default speed is assumed along the radar-estimated heading."
    el.append(P(note))
    el.append(two_col("Projects the position forward at constant speed and heading, widening a circle of uncertainty for drift and speed error.",
                      "Where to look next. It is not where the ship will be: it assumes straight, steady travel and says nothing about intent."))
    el.append(method("src/analytics/risk_scorer.py, extrapolate_trajectory · reports/trajectory_validation.md"))

    # ============ Workflow =======================================================================
    tr = ctx.get("execution_trace") or []
    n_deg = len(ctx.get("degradation_notes") or [])
    el += section("Agent workflow", "Degraded" if n_deg else "Normal", need=4.0)
    fig("flow", W)
    el.append(ledger(["Step", "Node", "Status", "Time", "What happened"],
                     [[str(t.get("step_number")), t.get("agent_name"), t.get("status"), (f"{t['latency_ms']:.1f} ms" if t.get("latency_ms") is not None else "—"), t.get("notes") or t.get("action_taken")] for t in tr],
                     [W * 0.07, W * 0.25, W * 0.13, W * 0.11, W * 0.44], mono_cols=[1, 3]))
    if ctx.get("degradation_notes"):
        el.append(KeepTogether([Spacer(1, 6), Paragraph("Where evidence was missing", S["h3"])] + bullets(ctx["degradation_notes"])))
    el.append(two_col("Seven software steps run in order: mission set-up, radar-to-AIS matching, feature engineering, sanctions screening, risk assessment, an optional human step, and report writing.",
                      "Which evidence each step used, how long it took, and where data was missing or the run fell back to a simpler mode."))
    el.append(method("src/agents/graph.py · reports/agentic_ai_audit.md"))

    # ============ Human review ===================================================================
    el += section("Human review and audit trail", "Required" if ctx.get("human_in_the_loop_required") else "Not required")
    dec = ctx.get("hitl_decisions") or []
    if dec:
        el.append(ledger(["Time (UTC)", "Decision", "Analyst notes"], [[str(x.get("timestamp"))[:16].replace("T", " "), x.get("disposition"), x.get("notes")] for x in dec], [W * 0.20, W * 0.16, W * 0.64], mono_cols=[0]))
    elif ctx.get("human_in_the_loop_required"):
        el.append(P("A person must decide this case. No decision had been recorded when this report was produced."))
    else:
        el.append(P("The risk gate did not require a person to decide this case."))
    lc = d["ledger_check"]
    el.append(P(f"The audit ledger holds {lc['length']} entries and its hash chain {'verifies' if lc['valid'] else 'is BROKEN at entry ' + str(lc['broken_at'])}. Head: {str(lc['head'])[:24]}.", "small"))
    if d["case_ledger"]:
        el.append(ledger(["Entry", "Time (UTC)", "Action", "By"], [[str(e["index"]), str(e["timestamp"])[:19].replace("T", " "), e["action"], e["operator"]] for e in d["case_ledger"]],
                         [W * 0.09, W * 0.28, W * 0.45, W * 0.18], mono_cols=[0, 1, 2, 3]))

    # ============ Legal ==========================================================================
    el += section("Legal basis", "Context")
    el.append(P("Statutory text comes from a fixed catalogue; a language model never writes it.", "small"))
    cited = [x for x in d["legal"] if x["triggered"]]
    for lg in cited:
        el.append(KeepTogether([Paragraph(esc(lg["title"]), S["h3"]), P(lg["statute"]),
                                P(M(f'<font name="{SANS_M}">Why it applies:</font> {esc(lg["why"])}'), "small"), P(lg["link"] or "", "small")]))
    if not cited:
        el.append(P("No statute was triggered by the evidence."))
    rest = [x for x in d["legal"] if not x["triggered"]]
    if rest:
        el.append(Spacer(1, 6))
        el.append(Paragraph("Considered and not cited", S["h3"]))
        el.append(ledger(["Provision", "Why it was not cited"], [[x["title"], x["why"].replace("Not cited: ", "")] for x in rest], [W * 0.38, W * 0.62]))

    # ============ Explanations ===================================================================
    el += section("Explanations, in order of how well the evidence fits", need=4.5)
    rank = {"CERTAIN": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    first = {"name": "AIS switched off on purpose", "for": risk.get("risk_factors") or [], "against": ["A radar detection alone cannot show intent."],
             "weight": "HIGH" if (prob or 0) >= 0.7 else ("MEDIUM" if (prob or 0) >= 0.4 else "LOW"), "settle": "A second, independent AIS receiver feed or a satellite pass at the same time."}
    hyps = sorted([first] + d["hypotheses"], key=lambda h: rank.get(h["weight"], 4))
    el.append(ledger(["#", "Explanation", "Fit", "Evidence for", "Evidence against"],
                     [[str(i + 1), h["name"], h["weight"].lower(), "; ".join(h["for"]) or "nothing recorded", "; ".join(h["against"]) or "nothing recorded"] for i, h in enumerate(hyps)],
                     [W * 0.05, W * 0.24, W * 0.09, W * 0.32, W * 0.30]))
    el.append(Spacer(1, 8))
    el.append(Paragraph("WHAT WOULD SETTLE IT", S["label"]))
    el.append(Spacer(1, 3))
    seen: List[str] = []
    for h in hyps:
        if h["settle"] not in seen:
            seen.append(h["settle"])
    el += bullets(seen[:5])

    el += section("Checks that came back normal or could not run", need=3.4)
    el.append(ledger(["Check", "Result", "Here"], [[c["check"], c["result"], c["here"]] for c in d["checks"]], [W * 0.26, W * 0.16, W * 0.58]))
    el.append(Spacer(1, 6))
    el.append(Paragraph("What this assessment cannot tell you", S["h3"]))
    el += bullets(d["limitations"])

    # ============ Appendices =====================================================================
    el.append(PageBreak())
    el += section("Evidence ledger", rule=False)
    el.append(P("Every engineered feature behind this assessment. Values marked n/a had no AIS candidate to compute from.", "small"))
    dom_names = {"sar": "Radar", "ais": "AIS track", "geospatial": "Geography", "historical": "History", "fusion": "Fusion"}
    rows = []
    for r in d["features"]:
        val = fmt(r["value"]) if r["value"] is not None else ("n/a" if "n/a" in (r["note"] or "") else "—")
        rows.append([r["name"], dom_names[r["domain"]], val, r["description"] + (f" ({r['formula']})" if r["formula"] else "")])
    el.append(ledger(["Feature", "Class", "Value", "Meaning"], rows, [W * 0.28, W * 0.12, W * 0.12, W * 0.48], mono_cols=[0, 2]))

    el += section("Where the data comes from")
    prov_rows = [[k, M(f'<font name="{MONO}" size="7" color="{ACCENT_HEX if val in ("UNAVAILABLE", "SYNTHETIC") else MUTED_HEX}">{val}</font>')] for k, val in d["provenance"].items()]
    el.append(ledger(["Input", "Provenance"], prov_rows, [W * 0.55, W * 0.45]))
    el.append(Spacer(1, 6))
    el.append(ledger(["Asset", "Provenance", "Count", "Source"],
                     [[a["name"], a["provenance"], fmt(a.get("count")), (a.get("source", "") + " " + a.get("details", "")).strip()] for a in d["inventory"].get("assets", [])],
                     [W * 0.27, W * 0.14, W * 0.10, W * 0.49]))
    inv = {a["id"]: a for a in (d["inventory"].get("assets") or [])}
    hashes = [f"{inv[k]['name']}: {inv[k].get('sha256')}" for k in ("sdn.xml", "un_consolidated.xml") if k in inv]
    if hashes:
        el.append(Spacer(1, 4))
        el += [Paragraph(esc(h), S["mono"]) for h in hashes]

    el += section("Integrity and reproduction")
    el.append(ledger(["Item", "Value"], [["Evidence hash (SHA-256)", d["evidence_hash"]], ["Audit chain head", str(lc["head"])], ["Software", json.dumps(d["versions"])], ["Narrative", narrative.get("label", "")]],
                     [W * 0.28, W * 0.72], mono_cols=[1]))
    trimmed = {k: v_ for k, v_ in req.items() if k not in ("all_detections", "ground_truth_ais")}
    el.append(Spacer(1, 6))
    el.append(Paragraph("REQUEST THAT PRODUCED THIS REPORT", S["label"]))
    el.append(Spacer(1, 3))
    el.append(Paragraph(esc(json.dumps(trimmed, default=str)[:2600]), S["mono"]))
    el.append(Spacer(1, 6))
    el.append(P("Send this request to POST /api/investigate. The deterministic stages (features, scoring, forecast, sanctions) return identical values for identical inputs.", "small"))

    doc.build(el, canvasmaker=make_canvas(meta))
    return buf.getvalue()
