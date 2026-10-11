"""Forensic analysis report renderer.

A formal, black-and-white, numbered-paragraph report in the structure used for technical expert
reports: purpose and scope, summary of findings, materials examined and chain of custody,
methodology, detailed findings, alternative explanations, reliability and limitations, legal
provisions referenced, audit trail, reproducibility, and an examiner's statement.

The report is produced by automated analysis. It never states more than the evidence supports, it
discloses the evidentiary status of every input (observed, withheld or test data), and it leaves the
examiner's certification blank until a qualified person completes it. Whether any report is
admissible is for the tribunal and depends on the jurisdiction and the examiner; this document only
supplies the information such a review normally needs.
"""

import io
import json
import os
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Frame, Image, KeepTogether, PageBreak, PageTemplate, Paragraph, Spacer, Table,
                                TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

BLACK = colors.black
GREY = colors.HexColor("#555555")
RULE = colors.HexColor("#999999")
HEADFILL = colors.HexColor("#E4E4E4")
PAGE_W, PAGE_H = LETTER
ML = MR = 1.0 * inch
W = PAGE_W - ML - MR

SERIF, SERIF_B, SERIF_I, MONO = "Times-Roman", "Times-Bold", "Times-Italic", "Courier"

_REPLACE = {"≥": ">=", "≤": "<=", "→": "to", "↔": "to", "≈": "~", "Δ": "delta", "✓": "yes", "π": "pi", "θ": "theta", "Σ": "sum", "σ": "sigma",
            "−": "-", "‑": "-", "µ": "u", "λ": "lambda", "′": "'", "″": '"', " ": " ", " ": " ", " ": " "}


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
    "title": ParagraphStyle("title", fontName=SERIF_B, fontSize=20, leading=25, alignment=TA_CENTER, spaceAfter=6),
    "subtitle": ParagraphStyle("subtitle", fontName=SERIF, fontSize=12, leading=16, alignment=TA_CENTER, textColor=GREY, spaceAfter=14),
    "h1": ParagraphStyle("h1", fontName=SERIF_B, fontSize=13, leading=17, spaceBefore=14, spaceAfter=6, keepWithNext=1),
    "h2": ParagraphStyle("h2", fontName=SERIF_B, fontSize=11.2, leading=15, spaceBefore=9, spaceAfter=4, keepWithNext=1),
    "toc": ParagraphStyle("toc", fontName=SERIF, fontSize=11, leading=17),
    "body": ParagraphStyle("body", fontName=SERIF, fontSize=10.8, leading=15, alignment=TA_JUSTIFY, spaceAfter=5),
    "num": ParagraphStyle("num", fontName=SERIF, fontSize=10.8, leading=15, alignment=TA_JUSTIFY, leftIndent=34, firstLineIndent=-34, spaceAfter=5),
    "cap": ParagraphStyle("cap", fontName=SERIF_I, fontSize=9.4, leading=12.4, spaceBefore=3, spaceAfter=9, alignment=TA_LEFT),
    "capt": ParagraphStyle("capt", fontName=SERIF_B, fontSize=9.6, leading=12.4, spaceBefore=8, spaceAfter=3, keepWithNext=1),
    "cell": ParagraphStyle("cell", fontName=SERIF, fontSize=9.4, leading=12),
    "cellb": ParagraphStyle("cellb", fontName=SERIF_B, fontSize=9.4, leading=12),
    "mono": ParagraphStyle("mono", fontName=MONO, fontSize=7.8, leading=10),
    "small": ParagraphStyle("small", fontName=SERIF, fontSize=9.2, leading=12, textColor=GREY),
    "box": ParagraphStyle("box", fontName=SERIF, fontSize=10.2, leading=14, alignment=TA_JUSTIFY),
}


def fmt(v: Any, nd: int = 2) -> str:
    if v is None:
        return "not available"
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


def grid(header: List[str], rows: List[List[Any]], widths: List[float], mono_cols: Optional[List[int]] = None) -> Table:
    mono_cols = mono_cols or []
    data = [[Paragraph(esc(h), S["cellb"]) for h in header]]
    for r in rows:
        data.append([c if hasattr(c, "wrap") else Paragraph(_cell(c), S["mono"] if i in mono_cols else S["cell"]) for i, c in enumerate(r)])
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, BLACK), ("BACKGROUND", (0, 0), (-1, 0), HEADFILL), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    return t


def keyval(rows: List[List[Any]], w1: float = 2.0 * inch) -> Table:
    data = [[Paragraph(esc(k), S["cellb"]), c if hasattr(c, "wrap") else Paragraph(_cell(c), S["cell"])] for k, c in rows]
    t = Table(data, colWidths=[w1, W - w1])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, BLACK), ("BACKGROUND", (0, 0), (0, -1), HEADFILL), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    return t


def boxed(text: str, title: Optional[str] = None) -> Table:
    inner: List[Any] = []
    if title:
        inner.append(Paragraph(esc(title), S["cellb"]))
        inner.append(Spacer(1, 3))
    inner.append(Paragraph(esc(text), S["box"]))
    t = Table([[inner]], colWidths=[W])
    t.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 1.0, BLACK), ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                           ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
    return t


class Doc(BaseDocTemplate):
    def __init__(self, buf, meta):
        super().__init__(buf, pagesize=LETTER, leftMargin=ML, rightMargin=MR, topMargin=1.0 * inch, bottomMargin=0.95 * inch,
                         title=f"Forensic Analysis Report {meta['report_id']}", author="DVD-MDA automated analysis", subject="Maritime surveillance analysis")
        frame = Frame(ML, 0.95 * inch, W, PAGE_H - 1.95 * inch, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0, id="f")
        self.addPageTemplates([PageTemplate(id="p", frames=[frame])])
        self._keys = 0

    def afterFlowable(self, fl):
        if isinstance(fl, Paragraph) and fl.style.name in ("h1", "h2") and getattr(fl, "_toc", True):
            text = fl.getPlainText()
            key = "sec-" + "".join(ch if ch.isalnum() else "-" for ch in text)[:48]  # stable across multiBuild passes
            self.canv.bookmarkPage(key)
            self.notify("TOCEntry", (0 if fl.style.name == "h1" else 1, text, self.page, key))


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
            self.setFont(SERIF, 8.6)
            self.drawString(ML, PAGE_H - 0.62 * inch, f"Forensic Analysis Report {meta['report_id']}")
            self.drawRightString(PAGE_W - MR, PAGE_H - 0.62 * inch, "CONFIDENTIAL - ANALYTICAL WORK PRODUCT")
            self.setStrokeColor(BLACK)
            self.setLineWidth(0.6)
            self.line(ML, PAGE_H - 0.70 * inch, PAGE_W - MR, PAGE_H - 0.70 * inch)
            self.line(ML, 0.78 * inch, PAGE_W - MR, 0.78 * inch)
            self.setFont(SERIF, 8.6)
            self.drawString(ML, 0.58 * inch, f"Matter: {meta['matter']}")
            self.drawCentredString(PAGE_W / 2, 0.58 * inch, f"Page {self._pageNumber} of {total}")
            self.setFont(MONO, 7)
            self.drawRightString(PAGE_W - MR, 0.58 * inch, f"SHA-256 {meta['hash'][:16]}")
            self.restoreState()

    return NumberedCanvas


def evidentiary_status(ctx: Dict[str, Any]) -> Dict[str, str]:
    req = ctx.get("request") or {}
    if req.get("chip_id"):
        if req.get("simulate_ais_offline"):
            return {"label": "Observed radar data; AIS record withheld for the analysis",
                    "text": ("The radar image is an observed Sentinel-1 acquisition. The AIS record that the source dataset associates with this image was deliberately "
                             "withheld from the analysis at the operator's request. The finding that no AIS broadcast was correlated therefore reflects that controlled condition. "
                             "It is not an observation that the vessel stopped transmitting.")}
        return {"label": "Observed radar data and observed AIS record", "text": "Both the radar image and the AIS record are observed data taken from the source dataset identified in Section 3."}
    return {"label": "Test scenario (not an observation of a real event)",
            "text": ("The inputs to this analysis are a constructed test scenario used to exercise the software. They are not observations of a real vessel or event. "
                     "Nothing in this report may be relied on as evidence that any real incident occurred.")}


class Num:
    """Numbered-paragraph helper: sections 1, 2, ...; paragraphs 3.1, 3.2, ...; subsections 5.1 with paragraphs 5.1.1."""

    def __init__(self, el: List[Any]):
        self.el, self.s, self.sub, self.p = el, 0, 0, 0
        self.fig, self.tab = 0, 0

    def h1(self, title: str, page_break: bool = False) -> None:
        self.s += 1
        self.sub = 0
        self.p = 0
        if page_break:
            self.el.append(PageBreak())
        self.el.append(Paragraph(f"{self.s}.&nbsp;&nbsp;{esc(title)}", S["h1"]))

    def h2(self, title: str) -> None:
        self.sub += 1
        self.p = 0
        self.el.append(Paragraph(f"{self.s}.{self.sub}&nbsp;&nbsp;{esc(title)}", S["h2"]))

    def para(self, text: Any) -> None:
        self.p += 1
        label = f"{self.s}.{self.sub}.{self.p}" if self.sub else f"{self.s}.{self.p}"
        self.el.append(Paragraph(f'<font name="{SERIF_B}">{label}</font>&nbsp;&nbsp;&nbsp;{_cell(text)}', S["num"]))

    def table(self, caption: str, flow: Any) -> None:
        self.tab += 1
        self.el.append(Paragraph(f"Table {self.tab}. {esc(caption)}", S["capt"]))
        self.el.append(flow)
        self.el.append(Spacer(1, 8))

    def figure(self, caption: str, png: Optional[bytes], width: float) -> None:
        im = img(png, width)
        if im is None:
            return
        self.fig += 1
        self.el.append(KeepTogether([im, Paragraph(f"Figure {self.fig}. {esc(caption)}", S["cap"])]))


def render(d: Dict[str, Any], narrative: Dict[str, Any], figs: Dict[str, Optional[bytes]]) -> bytes:
    ctx = d["ctx"]
    rep = ctx.get("report") or {}
    det = ctx.get("detection") or {}
    risk = ctx.get("risk_assessment") or {}
    geo = ctx.get("geo_context") or {}
    sanc = ctx.get("sanctions") or {}
    fusion = (ctx.get("features") or {}).get("fusion") or {}
    ais_rec = ctx.get("ais_used")
    forecast = ctx.get("forecast") or {}
    req = ctx.get("request") or {}
    status = evidentiary_status(ctx)
    prob = risk.get("dark_vessel_probability")
    corr = bool(fusion.get("is_spatially_correlated"))
    is_real = bool(req.get("chip_id"))
    tier = (rep.get("threat_tier") or "not assigned")
    report_id = rep.get("report_id", ctx.get("mission_id"))
    matter = str(req.get("scenario_id") or req.get("chip_id") or ctx.get("mission_id"))
    inv = {a["id"]: a for a in (d["inventory"].get("assets") or [])}
    length = det.get("length_m") or 0.0
    lc = d["ledger_check"]

    meta = {"report_id": report_id, "matter": matter[:46], "hash": d["evidence_hash"]}
    buf = io.BytesIO()
    doc = Doc(buf, meta)
    el: List[Any] = []
    n = Num(el)

    # ------------------------------------------------------------------ cover -------------
    el.append(Spacer(1, 0.5 * inch))
    el.append(Paragraph("FORENSIC ANALYSIS REPORT", S["title"]))
    el.append(Paragraph("Maritime surveillance evidence: radar detection, AIS correlation and sanctions screening", S["subtitle"]))
    el.append(Table([[""]], colWidths=[W], rowHeights=[2], style=TableStyle([("LINEABOVE", (0, 0), (-1, 0), 1.2, BLACK)])))
    el.append(Spacer(1, 10))
    el.append(keyval([
        ["Report number", report_id], ["Matter reference", matter], ["Date of report (UTC)", str(d["generated_at"])[:19].replace("T", " ")],
        ["Analysis run (UTC)", str(ctx.get("created_at", ""))[:19].replace("T", " ")], ["Subject of analysis", f"Radar detection {det.get('detection_id', '')} at {det.get('latitude', 0):.5f}, {det.get('longitude', 0):.5f}"],
        ["Evidentiary status of inputs", status["label"]], ["Prepared by", f"DVD-MDA automated analysis system (software revision {d['versions'].get('git_sha')})"],
        ["Prepared for", "______________________________________________"], ["Integrity (SHA-256 of evidence record)", M(f'<font name="{MONO}" size="7.4">{d["evidence_hash"]}</font>')],
    ]))
    el.append(Spacer(1, 12))
    el.append(boxed("This report was produced by automated analysis software. It has not been reviewed, adopted or certified by a human examiner unless the examiner's statement in Section 11 "
                    "has been completed and signed. The assessment is expressed as a probability based on rule-based indicators; it is not a finding of fact and it does not establish intent.",
                    "Status of this report"))
    el.append(Spacer(1, 12))
    el.append(boxed(status["text"], "Evidentiary status of the inputs"))
    el.append(PageBreak())
    toc = TableOfContents()
    toc.levelStyles = [ParagraphStyle("t0", fontName=SERIF_B, fontSize=10.8, leading=16), ParagraphStyle("t1", fontName=SERIF, fontSize=10.2, leading=14, leftIndent=18)]
    el.append(Paragraph("Contents", ParagraphStyle("ch", fontName=SERIF_B, fontSize=13, leading=17, spaceAfter=8)))
    el.append(toc)
    el.append(PageBreak())

    # ------------------------------------------------------------------ 1 ------------------
    n.h1("Purpose and scope")
    n.para("This report records what an automated analysis found when a single radar detection was examined against automatic identification system (AIS) records, "
           "sanctions registries and maritime-zone data. The question addressed is whether the detection is explained by an AIS-transmitting vessel and, if it is not, how strongly the "
           "available indicators point to a vessel that is not transmitting AIS.")
    n.para("The report does not address the identity, ownership or conduct of any person. It does not offer a legal conclusion. Statutory provisions are referenced in Section 8 only to show which "
           "provisions the stated indicators would be relevant to.")
    n.para(f"The matter reference is {matter}. Exhibit identifiers (E-1 to E-6) are used throughout and are described in Section 3.")

    # ------------------------------------------------------------------ 2 ------------------
    n.h1("Summary of findings")
    if corr:
        s1 = f"The radar detection was matched to an AIS broadcast within the correlation gate of 15 km and 60 minutes (Section 5.2)."
    else:
        s1 = ("No AIS broadcast was matched to the radar detection within the correlation gate of 15 km and 60 minutes"
              + (", because the AIS record was withheld from the analysis (Section 5.2)." if (is_real and req.get("simulate_ais_offline")) else " (Section 5.2)."))
    n.para(f"A ship-sized radar target about {length:.0f} m long and {det.get('width_m') or 0:.0f} m wide was detected with detector confidence {det.get('confidence') or 0:.2f} (Section 5.1).")
    n.para(s1)
    n.para("The sanctions screen " + (f"returned a registry match for {sanc.get('query_target')} (Section 5.4)." if sanc.get("is_sanctioned") else "returned no registry match for the identifiers available (Section 5.4)."))
    n.para(("The position lies inside the maritime-zone dataset used (Section 5.3)." if geo.get("in_coverage", True) else "The position lies outside the maritime-zone dataset used, so no jurisdictional analysis was possible (Section 5.3)."))
    if prob is not None:
        n.para(f"The rule-based assessment assigns a dark-vessel probability of {prob:.2f} and the classification {str(risk.get('dark_vessel_classification', '')).replace('_', ' ').lower()}; "
               f"the resulting threat tier is {tier} (Section 5.5). The probability is a ranking aid, not a measured likelihood.")
    n.para("On the data examined, the observations are " + ("consistent with an AIS-transmitting vessel." if corr else "consistent with a vessel that was not transmitting AIS at the time of acquisition, but they are equally consistent with the alternative explanations in Section 6. They do not establish intent."))

    # ------------------------------------------------------------------ 3 ------------------
    n.h1("Materials examined and chain of custody")
    n.para("The table below lists each input examined, its origin, and a cryptographic hash where a file exists. Hashes allow a reviewer to confirm that the files they hold are identical to those analysed.")
    chip_hash = None
    if is_real:
        try:
            from src.data import real_cases
            chip_hash = real_cases.sha256_file(real_cases.chip_path(req["chip_id"]))
        except Exception:
            chip_hash = None
    rows = [
        ["E-1", "Radar acquisition", (f"Sentinel-1 dual-polarisation chip {req.get('chip_id')} (scene {det.get('scene_id')})" if is_real else f"Test scenario input (scene label {det.get('scene_id')})"),
         (req.get("provenance") or {}).get("source", "Operator-supplied") if is_real else "Constructed test fixture", chip_hash or "no file (input record only)"],
        ["E-2", "AIS record", ("Withheld from the analysis at the operator's request" if (is_real and req.get("simulate_ais_offline")) else (f"{ais_rec.get('vessel_name') or ais_rec.get('mmsi')} (MMSI {ais_rec.get('mmsi')}) at {ais_rec.get('timestamp')}" if ais_rec else "None supplied")),
         "Source dataset" if is_real else "Constructed test fixture", "input record only"],
        ["E-3", "Sanctions registries", "OFAC SDN list; UN Security Council consolidated list", "Official publications (U.S. Treasury; United Nations)",
         "; ".join(f"{inv[k]['name']}: {inv[k].get('sha256')}" for k in ("sdn.xml", "un_consolidated.xml") if k in inv) or "not recorded"],
        ["E-4", "Maritime-zone dataset", "Regional EEZ polygons (Arabian Sea) and corridor definitions", "Bundled dataset; exact upstream source not recorded", (inv.get("eez") or {}).get("sha256") or "not recorded"],
        ["E-5", "Detector weights", "YOLO ship-detection network", "Trained model supplied with the software", (inv.get("detector") or {}).get("sha256") or "not recorded"],
        ["E-6", "Analysis software", f"Revision {d['versions'].get('git_sha')}; Python {d['versions'].get('python')}", "DVD-MDA", "see Section 10"],
    ]
    n.table("Materials examined", grid(["Ref.", "Item", "Description", "Origin", "SHA-256 / note"], rows, [0.4 * inch, 1.0 * inch, 1.75 * inch, 1.35 * inch, W - 4.5 * inch], mono_cols=[4]))
    n.para("Handling: inputs were read, not modified. The analysis record, including every input value, was hashed after the run (Section 10). Any later change to the record changes that hash.")

    # ------------------------------------------------------------------ 4 ------------------
    n.h1("Methodology")
    n.para("The analysis follows seven automated steps, run in a fixed order by a state-machine workflow. A human review step is added only when the assessed risk is high. The steps are:")
    steps = [
        ["1", "Mission set-up", "Fixes the area, time window and position of the detection; resolves the maritime-zone context."],
        ["2", "SAR-AIS correlation", "Searches the AIS records for a broadcast within 15 km and 60 minutes of the radar position and scores candidates on distance (weight 0.6) and time (weight 0.4)."],
        ["3", "Feature engineering", f"Computes {len(d['features'])} features across radar, AIS, geography, history and fusion domains (Appendix A)."],
        ["4", "Sanctions screening", "Compares IMO, MMSI and name against the OFAC SDN and UN consolidated lists (exact identifier match first, then fuzzy name match)."],
        ["5", "Risk assessment", "Applies the fixed scoring rules listed below and a dead-reckoning forecast at +6, +12 and +24 hours."],
        ["6", "Human review", "Required when the anomaly score reaches the high-risk gate or a sanctions match exists; records the examiner's disposition."],
        ["7", "Report preparation", "Assembles this report from the stored evidence record."],
    ]
    n.table("Analysis steps", grid(["Step", "Name", "Operation"], steps, [0.45 * inch, 1.4 * inch, W - 1.85 * inch]))
    n.para("Radar detection uses a neural network. Length and beam are taken from the detected bounding box at the sensor's 10 m pixel spacing; contrast is measured against a 15-pixel ring of surrounding sea. "
           "All other steps are deterministic code and return identical results for identical inputs.")
    rules = [["Starting probability for a radar target with no AIS match", "0.50"], ["Length below 30 m (AIS-exempt craft)", "-0.35"], ["Length of 100 m or more (AIS mandatory)", "+0.30"],
             ["More than 100 km from the coast (only where zone data cover the position)", "+0.15"], ["Within 80 km of a ship-to-ship corridor (only where zone data cover the position)", "+0.15"],
             ["AIS silent for 12 hours or more", "+0.10"], ["Sensor blackout recorded", "capped to 0.40-0.65"], ["Correlated with an AIS broadcast", "set to 0.05"],
             ["Probability of 0.70 or more is classed as deliberate dark-vessel behaviour; 0.40 or more as AIS shadow zone", "classification"]]
    n.table("Scoring rules (fixed in the software)", grid(["Rule", "Effect on probability"], rules, [W - 1.7 * inch, 1.7 * inch]))

    # ------------------------------------------------------------------ 5 ------------------
    n.h1("Findings", page_break=True)
    n.h2("Radar detection")
    tcr = det.get("target_clutter_ratio_db")
    n.para(f"The detector identified a target of estimated length {length:.1f} m and beam {det.get('width_m') or 0:.1f} m (aspect ratio {fmt(det.get('aspect_ratio'))}) at "
           f"{det.get('latitude', 0):.5f}, {det.get('longitude', 0):.5f}, with confidence {det.get('confidence') or 0:.2f}"
           + (f". Mean backscatter exceeded that of the surrounding sea by {tcr:.1f} dB (uncalibrated)." if tcr else "."))
    n.para("Length and beam are quantised to the 10 m pixel spacing, so each carries an uncertainty of about 10 m. The heading estimate is derived from the bounding box and should be treated as coarse.")
    gt = req.get("ground_truth")
    if gt and gt.get("length_m") is not None:
        n.para(f"Validation point: for this acquisition the source dataset records the vessel's own reported length as {gt['length_m']:.0f} m. The measured length differs by {length - gt['length_m']:+.0f} m.")
    if is_real:
        n.figure("Radar chip (VV, VH and dual-polarisation composite). The examined target is boxed solid; other detections are boxed dashed.", figs.get("chip"), W)
        n.figure("Backscatter of the target compared with the surrounding sea.", figs.get("hist"), W * 0.62)
    else:
        n.para("No radar image exists for this test scenario. The figure below is a schematic drawn from the stated dimensions only and is not imagery.")
        n.figure("Schematic from stated dimensions (not imagery).", figs.get("schematic"), W * 0.62)
    alld = req.get("all_detections") or [det]
    if len(alld) > 1:
        n.table("All detections in the examined chip", grid(["Detection", "Confidence", "Length (m)", "Beam (m)", "Contrast (dB)"],
                [[x.get("detection_id", ""), fmt(x.get("confidence")), f"{x.get('length_m', 0):.0f}", f"{x.get('width_m', 0):.0f}", fmt(x.get("target_clutter_ratio_db"), 1)] for x in alld],
                [2.6 * inch, 0.9 * inch, 0.9 * inch, 0.8 * inch, W - 5.2 * inch], mono_cols=[0]))

    n.h2("AIS correlation")
    if corr:
        n.para(f"An AIS broadcast from {(ais_rec or {}).get('vessel_name') or (ais_rec or {}).get('mmsi')} was found within the gate. Speed over ground {fmt((ais_rec or {}).get('sog'), 1)} kn, course {fmt((ais_rec or {}).get('cog'), 0)} degrees.")
    elif is_real and req.get("simulate_ais_offline"):
        n.para("No AIS record was available to the analysis for this detection because the record was withheld at the operator's request. No inference about the vessel's actual transmissions is drawn from this.")
    else:
        n.para("No AIS broadcast was available within the gate for this detection. This shows that no matching broadcast was found in the records supplied. It does not show that the vessel did not transmit: the vessel may be outside receiver coverage, exempt from carriage requirements, or the records may be incomplete.")
    na = "not computed (no AIS candidate)"
    n.table("Correlation measures", grid(["Measure", "Value"], [
        ["Distance, radar position to AIS position", na if not ais_rec else f"{fmt(fusion.get('spatial_discrepancy_km'))} km (gate 15 km)"],
        ["Time difference", na if not ais_rec else f"{fmt(fusion.get('temporal_difference_minutes'))} min (gate 60 min)"],
        ["Length mismatch ratio", fmt(fusion.get("dimension_mismatch_ratio"))], ["Heading difference", fmt(fusion.get("heading_discrepancy_deg"))],
        ["Candidate identity score", na if not ais_rec else fmt(fusion.get("candidate_identity_score"))], ["Result", "Correlated" if corr else "Not correlated"]], [3.4 * inch, W - 3.4 * inch]))
    gaps = req.get("historical_gaps") or []
    if gaps:
        n.para(f"{len(gaps)} historical AIS transmission gap(s) were supplied for this vessel.")
        n.table("Historical AIS gaps", grid(["Gap starts", "Hours silent", "Last position", "Flagged"], [[g.get("gap_start"), fmt(g.get("duration_hours"), 1), f"{g.get('start_lat')}, {g.get('start_lon')}", "yes" if g.get("is_suspicious") else "no"] for g in gaps],
                [1.9 * inch, 1.0 * inch, 2.2 * inch, W - 5.1 * inch], mono_cols=[0, 2]))

    n.h2("Position and jurisdiction")
    n.para(rep.get("geospatial_eez_analysis", ""))
    if geo.get("in_coverage", True):
        n.table("Position measures", grid(["Measure", "Value"], [
            ["Inside an exclusive economic zone", f"{fmt(geo.get('inside_eez'))} ({geo.get('eez_country') or 'international waters'})"], ["Distance to coast", f"{fmt(geo.get('distance_to_coast_km'), 0)} km"],
            ["Distance to EEZ boundary", f"{fmt(geo.get('distance_to_eez_boundary_km'), 0)} km"], ["Nearest port", f"{geo.get('nearest_port_name')} ({fmt(geo.get('distance_to_nearest_port_km'), 0)} km)"],
            ["Nearest ship-to-ship corridor", f"{geo.get('nearest_sts_zone_name')} ({fmt(geo.get('distance_to_sts_zone_km'), 0)} km)"]], [3.0 * inch, W - 3.0 * inch]))
    else:
        n.para("The zone dataset covers the Arabian Sea only. Distances to its features would be measured across thousands of kilometres and carry no meaning for this position, so none are reported and the scoring rules ignore them.")
    n.figure("Position, forecast track and uncertainty circles. Dotted outlines show ship-to-ship corridors where the dataset applies.", figs.get("map"), W)

    n.h2("Sanctions screening")
    n.para(("The screen returned a registry match." if sanc.get("is_sanctioned") else "The screen returned no registry match.") + (f" {sanc.get('screening_notes')}" if (sanc.get("screening_notes") and sanc.get("is_sanctioned")) else ""))
    n.para(f"Identifiers screened: {sanc.get('query_target') or 'none available'}. Lists screened: {', '.join(sanc.get('screened_sources') or [])}. "
           "A registry match is a lead for the registry owner and is not proof of identity. Where no identifier is available, as for an unmatched radar target, the screen cannot return a meaningful result.")
    matches = sanc.get("matches") or []
    if matches:
        n.table("Registry matches", grid(["List", "Entity", "IMO / MMSI", "Programme", "Score", "Basis"],
                [[m.get("source_list"), m.get("entity_name"), f"{m.get('matched_imo') or '-'} / {m.get('matched_mmsi') or '-'}", ", ".join(m.get("sanction_programs") or []), fmt(m.get("match_score")), m.get("match_basis")] for m in matches],
                [0.9 * inch, 1.4 * inch, 1.3 * inch, 1.0 * inch, 0.5 * inch, W - 5.1 * inch], mono_cols=[2]))

    n.h2("Risk assessment")
    n.para(f"Applying the scoring rules in Section 4 to this record yields a dark-vessel probability of {fmt(prob)} (classification: {str(risk.get('dark_vessel_classification', '')).replace('_', ' ').lower()}), "
           f"an overall anomaly score of {fmt(risk.get('overall_anomaly_score'))} and threat tier {tier}. The anomaly score is 0.60 times the probability, plus 0.30 if a sanctions match exists (otherwise 0.05), plus 0.10 if the position is inside a mapped EEZ.")
    brk = (d.get("breakdown") or {}).get("rows") or []
    if brk:
        n.table("Derivation of the probability for this record", grid(["Step", "Change", "Running total"],
                [[r["label"], (f"{r['delta']:+.2f}" if r.get("delta") not in (None,) else "-"), f"{r['cumulative']:.2f}"] for r in brk], [W - 2.4 * inch, 1.1 * inch, 1.3 * inch]))
    n.para("Factors recorded: " + ("; ".join(f.rstrip(". ") for f in (risk.get("risk_factors") or [])) or "none") + ".")
    if d["counterfactuals"]:
        n.para("To show how sensitive the result is, the same deterministic scorer was re-run with one input changed at a time (table and figures below). A conclusion that survives these changes is more robust than one that does not.")
        n.table("Sensitivity of the probability to single input changes", grid(["Scenario", "Probability", "Classification", "Input changed"],
                [[r["label"], fmt(r["probability"]), r["classification"].replace("_", " ").lower(), r["change"]] for r in d["counterfactuals"]], [2.0 * inch, 0.9 * inch, 1.7 * inch, W - 4.6 * inch], mono_cols=[3]))
        n.figure("Probability under each changed input.", figs.get("cf"), W * 0.8)
        n.figure("Probability as a function of measured length, all else equal.", figs.get("sens"), W * 0.62)

    n.h2("Positional forecast")
    wps = forecast.get("extrapolated_waypoints") or []
    note = forecast.get("methodology_notes") or "Dead reckoning from the last speed and heading with a drift allowance that grows with time."
    if not ais_rec:
        note += " No AIS speed exists for this target, so a default speed is assumed along the radar-estimated heading."
    n.para(note + " The forecast assumes steady travel and says nothing about intent.")
    n.table("Dead-reckoning forecast", grid(["Horizon", "Latitude", "Longitude", "Uncertainty radius", "Time (UTC)"],
            [[f"+{w.get('projection_hours'):g} h", fmt(w.get("projected_lat"), 4), fmt(w.get("projected_lon"), 4), f"{fmt(w.get('uncertainty_radius_km'), 1)} km", str(w.get("projected_timestamp"))[:16].replace("T", " ")] for w in wps],
            [0.9 * inch, 1.1 * inch, 1.1 * inch, 1.5 * inch, W - 4.6 * inch], mono_cols=[1, 2, 4]))

    # ------------------------------------------------------------------ 6 ------------------
    n.h1("Alternative explanations considered")
    n.para("An assessment is only as sound as the alternatives it has weighed. The table below lists each explanation considered, the evidence for and against it, and what would settle it. 'Fit' is a qualitative rating from the stated rules, not a measured probability.")
    rank = {"CERTAIN": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    first = {"name": "AIS switched off deliberately", "for": risk.get("risk_factors") or [], "against": ["A radar detection alone cannot show intent."],
             "weight": "HIGH" if (prob or 0) >= 0.7 else ("MEDIUM" if (prob or 0) >= 0.4 else "LOW"), "settle": "A second, independent AIS receiver feed, or a satellite pass at the same time."}
    hyps = sorted([first] + d["hypotheses"], key=lambda h: rank.get(h["weight"], 4))
    n.table("Explanations considered", grid(["No.", "Explanation", "Fit", "Evidence for", "Evidence against", "Would settle it"],
            [[str(i + 1), h["name"], h["weight"].lower(), "; ".join(x.rstrip(". ") for x in h["for"]) or "none recorded", "; ".join(x.rstrip(". ") for x in h["against"]) or "none recorded", h["settle"]] for i, h in enumerate(hyps)],
            [0.35 * inch, 1.15 * inch, 0.62 * inch, 1.55 * inch, 1.45 * inch, W - 5.12 * inch]))

    # ------------------------------------------------------------------ 7 ------------------
    n.h1("Reliability, assumptions and limitations")
    n.para("The following addresses the questions a reviewer would normally ask about a technical method. Where the answer is unfavourable it is stated plainly.")
    rel = [
        ["Can the method be tested?", "Yes. Every deterministic stage returns identical output for identical input, and automated tests cover the scoring rules, correlation, screening and report generation."],
        ["Known error rate", "Length and beam: about 10 m (pixel quantisation). The overall classification has no independently established error rate; one has not been measured on an independent, labelled data set."],
        ["Peer review and publication", "The detector and scoring rules have not been peer reviewed. Internal validation notes exist (risk scorer, feature mathematics, trajectory, agent workflow) and are listed in the repository's reports directory."],
        ["Standards and controls", "Thresholds are fixed and documented (Section 4). They follow published conventions (for example the AIS carriage requirement of SOLAS Chapter V Regulation 19) but are not set by any standard."],
        ["General acceptance", "Ship detection in synthetic aperture radar imagery is widely used. This particular implementation and the composite risk score are not in general use."],
    ]
    n.table("Reliability factors", grid(["Question", "Answer"], rel, [1.7 * inch, W - 1.7 * inch]))
    n.para("Limitations of this assessment:")
    for i, item in enumerate(d["limitations"]):
        n.el.append(Paragraph(f"({chr(97 + i)})&nbsp;&nbsp;{esc(item)}", ParagraphStyle("li", parent=S["body"], leftIndent=54, firstLineIndent=-20, spaceAfter=3)))

    # ------------------------------------------------------------------ 8 ------------------
    n.h1("Legal provisions referenced")
    n.para("Provision text is taken from the software's fixed catalogue and was not generated by a language model. It should be checked against the official text before it is relied on.")
    cited = [x for x in d["legal"] if x["triggered"]]
    if not cited:
        n.para("No statutory provision was triggered by the indicators in this record.")
    for lg in cited:
        n.para(M(f'<font name="{SERIF_B}">{esc(lg["title"])}.</font> {esc(lg["statute"])} <font name="{SERIF_I}">Relevance: {esc(lg["why"])}</font>' + (f" Source: {esc(lg['link'])}." if lg.get("link") else "")))
    rest = [x for x in d["legal"] if not x["triggered"]]
    if rest:
        n.table("Provisions considered and not cited", grid(["Provision", "Reason not cited"], [[x["title"], x["why"].replace("Not cited: ", "")] for x in rest], [2.4 * inch, W - 2.4 * inch]))

    # ------------------------------------------------------------------ 9 ------------------
    n.h1("Audit trail and review")
    tr = ctx.get("execution_trace") or []
    n.para("The table below records each workflow step as executed, with its measured running time.")
    n.table("Workflow execution record", grid(["Step", "Node", "Status", "Time (ms)", "Note"],
            [[str(t.get("step_number")), t.get("agent_name"), t.get("status"), (f"{t['latency_ms']:.1f}" if t.get("latency_ms") is not None else "not recorded"), t.get("notes") or t.get("action_taken")] for t in tr],
            [0.4 * inch, 1.6 * inch, 0.9 * inch, 0.8 * inch, W - 3.7 * inch], mono_cols=[1]))
    if ctx.get("degradation_notes"):
        n.para("Conditions that degraded the analysis: " + " ".join(f"({i + 1}) {x}" for i, x in enumerate(ctx["degradation_notes"])))
    dec = ctx.get("hitl_decisions") or []
    if dec:
        n.table("Examiner decisions recorded", grid(["Time (UTC)", "Decision", "Notes"], [[str(x.get("timestamp"))[:19].replace("T", " "), x.get("disposition"), x.get("notes")] for x in dec], [1.5 * inch, 1.0 * inch, W - 2.5 * inch]))
    elif ctx.get("human_in_the_loop_required"):
        n.para("The risk gate required a human decision. None had been recorded when this report was produced.")
    else:
        n.para("The risk gate did not require a human decision for this record.")
    n.para(f"The audit ledger holds {lc['length']} entries. Its hash chain {'was verified as unbroken' if lc['valid'] else 'FAILED verification at entry ' + str(lc['broken_at'])}. Ledger head: {str(lc['head'])}.")
    if d["case_ledger"]:
        n.table("Ledger entries for this matter", grid(["Entry", "Time (UTC)", "Action", "Recorded by"], [[str(e["index"]), str(e["timestamp"])[:19].replace("T", " "), e["action"], e["operator"]] for e in d["case_ledger"]],
                [0.6 * inch, 1.7 * inch, 2.4 * inch, W - 4.7 * inch], mono_cols=[1, 2]))

    # ------------------------------------------------------------------ 10 -----------------
    n.h1("Reproducibility and integrity")
    n.para("A reviewer can reproduce the deterministic stages by submitting the request recorded below to the analysis software at the revision stated. Identical inputs return identical features, scores and forecasts. The radar detection step reproduces within floating-point tolerance on the same weights.")
    n.table("Integrity record", keyval([["Evidence record SHA-256", M(f'<font name="{MONO}" size="7.4">{d["evidence_hash"]}</font>')], ["Audit ledger head", M(f'<font name="{MONO}" size="7.4">{lc["head"]}</font>')],
              ["Software", json.dumps(d["versions"])], ["Narrative method", narrative.get("label", "")]], 1.8 * inch))
    trimmed = {k: v for k, v in req.items() if k not in ("all_detections", "ground_truth_ais")}
    n.table("Request that produced this record (JSON)", Paragraph(esc(json.dumps(trimmed, default=str)[:2400]), S["mono"]))
    if narrative.get("generated_by") == "LLM_VERIFIED":
        n.para("Narrative: the summary sentence in Section 1 of the working notes was drafted by a language model and then checked automatically; every number, tier, classification and jurisdiction in it matched the evidence record. No number or citation in this report originates from the model.")
        n.para("Model-drafted summary: " + (narrative.get("paragraphs") or [""])[0])

    # ------------------------------------------------------------------ 11 -----------------
    n.h1("Examiner's statement", page_break=True)
    n.para("To be completed by the qualified person who reviews this report. Until it is completed and signed, this document is automated analytical output only.")
    form = [["Name", ""], ["Qualifications and experience", ""], ["Organisation", ""], ["Scope of review (sections reviewed and adopted)", ""],
            ["Matters the examiner disagrees with or qualifies", ""], ["Statement of independence", ""], ["Signature", ""], ["Date", ""]]
    t = Table([[Paragraph(esc(k), S["cellb"]), ""] for k, _ in form], colWidths=[2.4 * inch, W - 2.4 * inch], rowHeights=[28, 40, 28, 40, 50, 36, 40, 28])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, BLACK), ("BACKGROUND", (0, 0), (0, -1), HEADFILL), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 5)]))
    el.append(t)

    # ------------------------------------------------------------------ appendices ---------
    el.append(PageBreak())
    el.append(Paragraph("Appendix A. Feature record", S["h1"]))
    el.append(Paragraph("Every engineered feature used in the analysis. 'not computed' means no AIS candidate existed to compute it from.", S["body"]))
    dom = {"sar": "Radar", "ais": "AIS track", "geospatial": "Geography", "historical": "History", "fusion": "Fusion"}
    rows = []
    for r in d["features"]:
        val = fmt(r["value"]) if r["value"] is not None else ("not computed" if "n/a" in (r["note"] or "") or "not computed" in (r["note"] or "") else "not available")
        rows.append([r["name"], dom[r["domain"]], val, r["description"] + (f" ({r['formula']})" if r["formula"] else "")])
    el.append(grid(["Feature", "Domain", "Value", "Definition"], rows, [1.85 * inch, 0.8 * inch, 0.9 * inch, W - 3.55 * inch], mono_cols=[0]))
    el.append(Paragraph("Appendix B. Glossary", S["h1"]))
    gl = [("AIS", "Automatic Identification System: ship transponder broadcasts of identity, position, speed and course."), ("SAR", "Synthetic aperture radar: active microwave imaging that works day and night through cloud."),
          ("EEZ", "Exclusive economic zone: waters up to 200 nautical miles from a coast (UNCLOS)."), ("STS", "Ship-to-ship transfer of cargo at sea."),
          ("Target-to-clutter ratio", "Mean target backscatter minus mean surrounding-sea backscatter, in decibels."), ("Dead reckoning", "Estimating a later position from an earlier position, speed and heading.")]
    el.append(grid(["Term", "Meaning"], [[a, b] for a, b in gl], [1.6 * inch, W - 1.6 * inch]))

    doc.multiBuild(el, canvasmaker=make_canvas(meta))
    return buf.getvalue()
