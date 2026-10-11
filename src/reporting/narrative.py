"""Narrative prose for the dossier.

Two producers, one verifier:
  * ``template_narrative``  — deterministic prose from the evidence (always available).
  * ``llm_narrative``       — the fine-tuned Qwen 2.5 model, used only if its files are loadable.
  * ``check_faithfulness``  — every number and statute in model-written text must exist in the
                              evidence/catalogue, otherwise the text is rejected and the template is used.
The LLM never computes numbers, probabilities, or legal conclusions.
"""

import json
import os
import re
import threading
from typing import Any, Dict, List, Optional, Tuple

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MERGED_DIR = os.path.join(ROOT, "models", "maritime_qwen_merged")
ADAPTER_DIR = os.path.join(ROOT, "models", "maritime_qwen_adapter")
BASE_MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"

SYSTEM_PROMPT = (
    "You are an expert maritime intelligence analyst synthesizing radar telemetry, AIS tracking, geospatial sovereignty data, "
    "and sanctions screening into formal, legally grounded maritime surveillance bulletins. Ensure every conclusion is directly "
    "grounded in sensor evidence and applicable maritime statutes (UNCLOS Art. 73, SOLAS V/19, OFAC)."
)

_llm_lock = threading.Lock()
_llm_state: Dict[str, Any] = {}


class LlmUnavailable(RuntimeError):
    pass


# ----------------------------------------------------------------------------------------------
# Deterministic narrative
# ----------------------------------------------------------------------------------------------

def template_narrative(facts: Dict[str, Any], hitl_decisions: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    f = facts
    prob = f.get("dark_vessel_probability")
    corr = f["ais_status"] == "Active Match"
    p1 = (
        f"Target {f['detection_id']} was detected by Sentinel-1 SAR at ({f['latitude']:.4f}, {f['longitude']:.4f}) with an estimated hull of "
        f"{f['length_m']:.0f} m × {f['width_m']:.0f} m (detector confidence {f['radar_confidence']:.2f}). "
        + ("It is explained by an active AIS broadcast" + (f" (MMSI {f['correlated_mmsi']})" if f.get("correlated_mmsi") else "") + "."
           if corr else "No AIS broadcast could be correlated with it within the spatio-temporal gate.")
    )
    p2 = (
        f"The deterministic scorer classifies the target as {f['classification']} with a dark-vessel probability of "
        f"{prob:.2f} and an overall anomaly score of {f['anomaly_score']:.2f}, giving threat tier {f['threat_tier']}. "
        if prob is not None else ""
    )
    if f.get("in_dataset_coverage", True):
        p3 = f"Jurisdiction: {f['jurisdiction']}; {f['distance_to_coast_km']:.0f} km from the nearest mapped coastline. "
    else:
        p3 = "The position lies outside the bundled EEZ/STS dataset, so no jurisdictional reasoning was applied. "
    p3 += "Sanctions screening: " + ("CONFIRMED registry match." if f["sanctions_hit"] else "no registry match.")
    if f["degradation_notes"]:
        p3 += f" The run was degraded ({f.get('degradation_count', len(f['degradation_notes']))} condition(s)); see the agent-workflow section."
    if hitl_decisions:
        p3 += f" An analyst recorded the decision {hitl_decisions[-1].get('disposition')}."
    findings = [
        f"Unmatched radar detection of a {f['length_m']:.0f} m vessel" if not corr else "Radar detection correlated with AIS",
        f"Classification {f['classification']} (p = {prob:.2f})" if prob is not None else "Classification unavailable",
        f"Threat tier {f['threat_tier']}",
        "Sanctions registry match" if f["sanctions_hit"] else "No sanctions registry match",
        "Geospatial context unavailable (outside dataset)" if not f.get("in_dataset_coverage", True) else f"Jurisdiction: {f['jurisdiction']}",
    ]
    return {"generated_by": "RULE_BASED", "label": "Rule-generated narrative", "paragraphs": [p for p in (p1, p2, p3) if p], "key_findings": findings, "issues": []}


# ----------------------------------------------------------------------------------------------
# Faithfulness verification
# ----------------------------------------------------------------------------------------------

_NUM = re.compile(r"-?\d+(?:\.\d+)?")


def _numbers_in(obj: Any) -> List[float]:
    out: List[float] = []
    if isinstance(obj, bool):
        return out
    if isinstance(obj, (int, float)):
        out.append(float(obj))
    elif isinstance(obj, str):
        out += [float(x) for x in _NUM.findall(obj)]
    elif isinstance(obj, dict):
        for v in obj.values():
            out += _numbers_in(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            out += _numbers_in(v)
    return out


def check_faithfulness(text: str, facts: Dict[str, Any], catalog: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    """Reject text with numbers not present in the evidence or statutes not in the catalogue."""
    issues: List[str] = []
    allowed = set()
    for n in _numbers_in(facts):
        for d in (0, 1, 2, 3):
            allowed.add(round(n, d))
    allowed |= {0.0, 1.0}
    for tok in _NUM.findall(text):
        v = float(tok)
        if round(v, 3) not in allowed and round(v, 2) not in allowed and round(v, 1) not in allowed and round(v, 0) not in allowed:
            issues.append(f"number {tok} not found in evidence")
    # Categorical claims must match the evidence exactly: threat tier, classification label, jurisdiction.
    tiers = r"(LOW|MEDIUM|HIGH|SEVERE|CRITICAL)"
    for m in re.finditer(tiers + r"\s*(?:threat\s*)?tier|tier\s*[:=]?\s*" + tiers + r"|\(" + tiers + r"\s*threat\)", text, flags=re.I):
        said = next(g for g in m.groups() if g).upper()
        if facts.get("threat_tier") and said != str(facts["threat_tier"]).upper():
            issues.append(f"threat tier '{said}' contradicts evidence ({facts['threat_tier']})")
    known = ("CORRELATED_BENIGN", "SMALL_CRAFT_EXEMPT", "AIS_SHADOW_ZONE", "SPOOFING_ANOMALY", "DELIBERATE_DARK_EVASION")
    for label in known:
        if label in text.upper() and facts.get("classification") and label != facts["classification"]:
            issues.append(f"classification '{label}' contradicts evidence ({facts['classification']})")
    jm = re.search(r"jurisdiction\s*[:=]\s*([A-Za-z ]+?)(?:[.;,\n]|$)", text, flags=re.I)
    if jm and facts.get("jurisdiction") and jm.group(1).strip().lower() != str(facts["jurisdiction"]).lower():
        issues.append(f"jurisdiction '{jm.group(1).strip()}' contradicts evidence ({facts['jurisdiction']})")
    cat_text = " ".join(f"{c['title']} {c['statute']}" for c in catalog).lower() + " " + " ".join(facts.get("statutes", [])).lower()
    for m in re.finditer(r"(?:article|art\.?|regulation|reg\.?)\s*(\d+)", text, flags=re.I):
        if m.group(1) not in re.findall(r"\d+", cat_text):
            issues.append(f"statute reference '{m.group(0)}' not in catalogue")
    return (not issues), issues


# ----------------------------------------------------------------------------------------------
# Optional LLM generation
# ----------------------------------------------------------------------------------------------

def llm_status() -> Dict[str, Any]:
    """Whether the fine-tuned model can actually be loaded, and if not, what is missing."""
    missing: List[str] = []
    merged_ok = os.path.exists(os.path.join(MERGED_DIR, "config.json")) and (
        os.path.exists(os.path.join(MERGED_DIR, "tokenizer.json")) or os.path.exists(os.path.join(MERGED_DIR, "tokenizer_config.json")))
    if merged_ok:
        return {"available": True, "mode": "merged", "missing": []}
    if not os.path.exists(os.path.join(MERGED_DIR, "model.safetensors")):
        missing.append("models/maritime_qwen_merged/model.safetensors")
    else:
        missing.append("models/maritime_qwen_merged/{config.json, tokenizer files}")
    adapter_cfg = os.path.exists(os.path.join(ADAPTER_DIR, "adapter_config.json"))
    if not adapter_cfg:
        missing.append("models/maritime_qwen_adapter/adapter_config.json")
    cache = os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub", "models--" + BASE_MODEL_ID.replace("/", "--"))
    base_cached = os.path.isdir(cache)
    if not base_cached:
        missing.append(f"base model {BASE_MODEL_ID} (not in the Hugging Face cache)")
    if adapter_cfg and base_cached:
        return {"available": True, "mode": "base+adapter", "missing": []}
    return {"available": False, "mode": None, "missing": missing}


def _load_llm() -> Tuple[Any, Any]:
    if "model" in _llm_state:
        return _llm_state["tok"], _llm_state["model"]
    st = llm_status()
    if not st["available"]:
        raise LlmUnavailable("Qwen model files incomplete: " + "; ".join(st["missing"]))
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32
    if st["mode"] == "merged":
        tok = AutoTokenizer.from_pretrained(MERGED_DIR)
        model = AutoModelForCausalLM.from_pretrained(MERGED_DIR, torch_dtype=dtype).to(device)
    else:
        from peft import PeftModel
        tok = AutoTokenizer.from_pretrained(BASE_MODEL_ID, local_files_only=True)
        base = AutoModelForCausalLM.from_pretrained(BASE_MODEL_ID, torch_dtype=dtype, local_files_only=True)
        model = PeftModel.from_pretrained(base, ADAPTER_DIR).to(device)
    model.eval()
    _llm_state.update({"tok": tok, "model": model, "device": device})
    return tok, model


def _telemetry_prompt(f: Dict[str, Any]) -> str:
    return (
        "ANALYZE MARITIME TARGET TELEMETRY:\n"
        f"- Target Detection ID: {f['detection_id']}\n"
        f"- Radar Coordinates: Lat {f['latitude']:.4f}, Lon {f['longitude']:.4f}\n"
        f"- SAR Dimensions: Length {f['length_m']:.1f}m, Beam {f['width_m']:.1f}m, Aspect Ratio {f['aspect_ratio']:.2f}\n"
        f"- Radar Confidence: {f['radar_confidence']:.2f}\n"
        f"- AIS Broadcast Status: {f['ais_status']}\n"
        f"- Correlated MMSI: {f.get('correlated_mmsi') or 'None'}\n"
        f"- Jurisdiction: {f['jurisdiction']}\n"
        f"- Distance to Coast: {(f.get('distance_to_coast_km') or 0):.1f} km\n"
        f"- Sanctions Hit: {f['sanctions_hit']} ({f.get('sanctions_risk')})\n"
        f"- Telemetry Degradation Notes: {'; '.join(f['degradation_notes']) or 'None'}\n\n"
        "Generate the validated, structured Intelligence Bulletin JSON."
    )


def llm_narrative(facts: Dict[str, Any], catalog: List[Dict[str, Any]], max_new_tokens: int = 700) -> Dict[str, Any]:
    """Generates the executive summary with the fine-tuned model, then verifies it against the evidence."""
    with _llm_lock:
        tok, model = _load_llm()
        import torch
        msgs = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": _telemetry_prompt(facts)}]
        enc = tok.apply_chat_template(msgs, add_generation_prompt=True, return_tensors="pt", return_dict=True)
        ids = enc["input_ids"].to(model.device)
        attn = enc["attention_mask"].to(model.device)
        with torch.no_grad():
            out = model.generate(input_ids=ids, attention_mask=attn, max_new_tokens=max_new_tokens, do_sample=False,
                                 repetition_penalty=1.0, eos_token_id=[151645, 151643], pad_token_id=151643)
        raw = tok.decode(out[0][ids.shape[1]:], skip_special_tokens=True).strip()
    cleaned = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise LlmUnavailable(f"model output was not valid JSON ({e})")
    summary = str(parsed.get("executive_summary", "")).strip()
    confidence = str(parsed.get("analyst_confidence_statement", "")).strip()
    if not summary:
        raise LlmUnavailable("model output had no executive_summary")
    ok, issues = check_faithfulness(summary + " " + confidence, facts, catalog)
    if not ok:
        raise LlmUnavailable("AI draft rejected by faithfulness check: " + "; ".join(issues[:4]))
    return {"generated_by": "LLM_VERIFIED", "label": "AI-drafted by fine-tuned Qwen 2.5 · numbers and citations verified against the evidence",
            "paragraphs": [summary] + ([confidence] if confidence else []), "issues": []}


def build_narrative(facts: Dict[str, Any], catalog: List[Dict[str, Any]], hitl: Optional[List[Dict[str, Any]]], use_llm: bool) -> Dict[str, Any]:
    base = template_narrative(facts, hitl)
    if not use_llm:
        return base
    try:
        ai = llm_narrative(facts, catalog)
        ai["key_findings"] = base["key_findings"]
        ai["rule_based_paragraphs"] = base["paragraphs"]
        return ai
    except Exception as e:  # any failure degrades to the verified template, never to unverified text
        base["issues"] = [f"AI narrative skipped: {e}"]
        return base
