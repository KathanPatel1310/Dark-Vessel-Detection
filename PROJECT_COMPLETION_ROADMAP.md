# Maritime Intelligence Project: End-to-End Completion Roadmap

This document is an execution brief for an AI coding agent working in this repository on the teammate's computer. Follow it in order, inspect the repository before changing it, and keep the work reproducible. This is a **pretrained-first plan**: reuse a suitable published SAR detector and acquire only enough labeled imagery to validate integration. Aim for **under 10 GB of additional working storage**; treat 15 GB as a hard ceiling unless the human owner approves a larger measured requirement.

The goal is a defensible academic prototype that processes actual SAR imagery, evaluates a ship detector, correlates detections with AIS evidence, runs the existing feature and LangGraph pipeline, and performs one real LLM fine-tuning experiment if the available hardware permits. It must clearly distinguish implemented work, downloaded source data, synthetic test data, and measured results.

## 1. Starting point and honest current status

The existing repository already contains:

- SAR, AIS, geospatial, and fusion feature engineering, plus a deterministic heuristic risk scorer and kinematic dead-reckoning in `src/features/` and `src/analytics/`.
- A LangGraph workflow and typed state in `src/agents/`, with conditional routing, degraded evidence handling, execution traces, and a human review checkpoint.
- OFAC/UN sanctions parsing and EEZ logic.
- A synthetic high-volume SAR table and synthetic AIS tracks created by `src/data/download_high_volume_bundle.py`. Despite filenames containing `real_`, these records are generated, not real satellite detections or real AIS tracks.
- Synthetic/rule-generated fine-tuning examples, a QLoRA training script, and an evaluation harness. No trained adapter is assumed to exist.
- Audit scripts/reports under `scripts/` and `reports/`. Their reported metrics are hypotheses to reproduce, not ground truth until rerun.

The existing main prediction is a rule-based evidential risk score and a rule-based vessel classification. The Random Forest in the ablation study is an experiment, not the live prediction component. A SAR detector added by this roadmap will detect vessels in imagery; SAR detection alone does not establish that a vessel is dark. Dark-vessel assessment requires time/location AIS correlation plus uncertainty handling.

## 2. Target system and completion definition

The finished demonstrator should follow this flow:

```text
Real SAR image / annotated SAR chip
    -> pretrained or lightly adapted SAR vessel detector
    -> image detection and confidence, box/mask, scene/time/location metadata
    -> image-derived SAR feature extraction
    -> time-and-distance-bounded AIS correlation and explicit match uncertainty
    -> existing engineered feature vector and heuristic risk assessment
    -> LangGraph investigation, degradation handling, trace, and human review
    -> optional fine-tuned LLM structured explanation/report
    -> validated report and reproducible evaluation artifacts
```

Completion means a new user can follow the repository instructions to reproduce the real-image inference/evaluation demo and the existing agent demo; see actual outputs and metrics; identify which inputs are real versus synthetic; and see an actual adapter training/evaluation run if hardware supports it. Do not mark the whole project complete just because scripts exist or a dry run passes.

## 3. Dataset and pretrained-model decision

Do not download both complete datasets by default. The first goal is to run a compatible published detector on a small real, labeled image subset. HRSID and xView3 are alternatives for evaluation/data compatibility; use both only when they add a specific, measured benefit. Their labels, sensor products, resolutions, and formats are not interchangeable.

### HRSID

- Role: manageable SAR ship-detection benchmark; use a small subset for compatibility testing or independent cross-dataset evaluation when the selected checkpoint has not seen its images.
- Published contents: 5,604 SAR images and 16,951 ship instances; the project repository describes JPG and higher-fidelity PNG variants and COCO-like annotations.
- Start with a **small subset** (for example 100–300 labeled chips), after measuring actual archive size. Prefer one distribution/representation if terms permit. Do not download both JPG and PNG copies.
- Record exact source URL, version/date, license/terms, archive size, extracted size, image count, annotation count, and checksum where practical.

### xView3-SAR

- Role: most directly relevant Sentinel-1 maritime detection/characterization test data, but scenes are large. Use only a few scenes or pre-cropped labeled chips, and only when compatible with the chosen detector.
- For pretrained-only inference, download a few labeled evaluation scenes/chips only; no training split is needed.
- If vision fine-tuning becomes necessary, only then download training data and split by **source scene** before cropping. No chip or overlapping scene may leak into the held-out test set.
- If evaluating an existing xView3 checkpoint, use only scenes proven absent from its training, pseudo-labeling, threshold tuning, and model-selection data. If provenance is unclear, do not report an xView3 score as independent.

### Pretrained detector policy (save time first)

1. Inspect the public xView3 challenge reference and published solution repositories for code, checkpoints, data compatibility, license, training-scene provenance, preprocessing, and input channels. Candidate references:
   - xView3 reference: <https://github.com/DIUx-xView/xview3-reference>
   - AI2/Skylight solution and downloadable trained model: <https://github.com/allenai/sar_vessel_detect>
   - HRSID dataset and annotation variants: <https://github.com/chaozhong2010/HRSID>
   - HRSID Faster R-CNN checkpoint candidate: <https://huggingface.co/PUSHPENDAR/hrsid-ship-detection>
2. Run one suitable published xView3/SAR checkpoint as a **pretrained baseline** before any training. Preserve its exact URL, hash, license, preprocessing, channels, and training-data provenance.
3. Choose the smallest valid labeled evaluation set after checking the checkpoint lineage and input compatibility. Prefer xView3 scenes not used by that checkpoint. If that cannot be established, use a small HRSID subset as a clearly labeled cross-dataset test only if the checkpoint accepts those inputs or a documented conversion preserves their semantics.
4. A candidate HRSID checkpoint may be tested if its architecture, weights, license, training split, and compatibility are verifiable. Do not assume a public checkpoint is independent of all HRSID images.
5. **Do not train/fine-tune the SAR detector in the primary path.** Consider a small adaptation only if inference fails due to a fixable domain/input gap and the owner agrees to the extra time and storage. Keep the published checkpoint baseline for comparison.
6. Do not use Prithvi EO as the default ship detector. Its published EO pretraining is based on optical Harmonized Landsat/Sentinel-2 inputs, so SAR sensor and task compatibility must be demonstrated before using it.

The primary route uses a pretrained computer-vision detector without adapting its weights. The text LLM fine-tuning experiment is separate and uses report examples, not SAR images. Vision fine-tuning remains a fallback, not a required project phase.

## 4. Storage budget and data acquisition gates

**Target: under 10 GB; hard cap: 15 GB of additional working storage** for downloaded datasets, model weights, caches, and outputs. Check free space and actual archive/extracted sizes before each download. The cap is a limit, not a target to fill. Git metadata and the existing source repository are outside this budget; do not commit datasets or model weights to Git.

Use this provisional allocation; measure actual archive/extracted sizes before downloading and revise the allocation with observed values:

| Item | Target ceiling | Notes |
|---|---:|---|
| One published SAR detector checkpoint and required runtime files | 0.5–2.5 GB | Measure actual checkpoint/repository size; avoid multiple candidate models. |
| Small labeled SAR evaluation subset (HRSID or xView3, not both initially) | 0.2–1.5 GB | Start with roughly 100–300 chips or the smallest few compatible scenes. |
| Optional second-dataset compatibility sample | 0–1 GB | Download only if the first pairing works and external validation adds value. |
| Filtered AIS sample and matched outputs | 0.05–0.3 GB | Use a small time/area/vessel subset, Parquet where appropriate. |
| Qwen base model, training cache, and one adapter/checkpoint | 2–4 GB | Exact needs depend on chosen size, quantization, sequence length, and framework cache. |
| Temporary cache, logs, figures, small margin | 1–1.5 GB | Use project-local caches; remove only reproducible temporary files. |
| **Planned total** | **roughly 4–10 GB** | Enforce the 15 GB ceiling; check actual sizes before downloading. |

These are rough planning estimates, not provider guarantees. Before every download, check exact archive size, extracted size, free space, terms, and required model cache. If the smallest usable subset exceeds the cap, stop and report observed sizes and alternatives. Do not download either full dataset in the primary path. Do not delete the only copy of source data or model files without confirming a reproducible copy exists.

### AIS source choice

Use AIS only to the extent needed for a geographically and temporally meaningful demonstration. Prefer a legitimately accessible filtered source such as Global Fishing Watch API/data (token and terms may apply) or an openly downloadable government archive suitable for the selected region. Record source, access date, terms, fields, coverage gaps, and filtering. Sources to inspect:

- Global Fishing Watch API documentation: <https://globalfishingwatch.org/our-apis/documentation/>
- GFW dataset descriptions/caveats: <https://api-doc.globalfishingwatch.org/our-apis/documentation/docs/v3/general-api-doc/data-caveats>
- NOAA MarineCadastre AccessAIS: <https://marinecadastre.gov/accessais/>

Do not call AIS-off event products definitive truth. Treat them as source-provided apparent events, and account for reception coverage and missingness. If a matching real AIS sample cannot be lawfully acquired within time/space limits, finish the SAR image demonstration and label the AIS match experiment as synthetic or unavailable rather than fabricating real matches.

### Download gate

Before the first download, create `reports/data_acquisition_manifest.md` with planned files, source links, license/terms, expected and actual bytes, free space, and chosen scene IDs. Download a small pilot first, verify that it opens and annotations parse, then proceed. If access requires credentials, have the human owner provide them locally; never place tokens in code, shell logs, Git, reports, or prompts.

## 5. Phase A — Host and repository preflight

1. Record commit, branch, dirty status, Python version, OS, CPU/RAM, GPU model/VRAM, CUDA/driver, disk free space, and versions of project dependencies.
2. Check for existing uncommitted user work; preserve it.
3. Create an isolated environment following the repository's supported setup. Do not upgrade packages blindly; pin a compatible reproducible set.
4. Run the existing test suite and end-to-end synthetic demo before changes. Save actual commands, exits, timings, warnings, and failures in `reports/project_completion_log.md`.
5. Inspect current data generator names and docs. Schedule correction of misleading `real_*` filenames/claims; retain compatibility only when necessary and annotate clearly.
6. Confirm remaining disk budget. If hardware/disk is insufficient for a chosen stage, do lower-cost inference or request a suitable cloud/Colab run; do not start a run likely to fill the disk.

## 6. Phase B — Acquire and document real SAR data

1. Check current HRSID and xView3 access instructions, versions, license/terms, formats, annotation schemas, checkpoint compatibility, and exact sizes from primary sources.
2. Select one dataset/checkpoint pairing based on verified provenance and compatible inputs. Start with a pilot of about 100 labeled chips or a few small scenes. Avoid a second dataset until the pilot runs end-to-end.
3. Download only the SAR channels and labels the pretrained detector needs. Keep source-scene identity and annotation provenance.
4. Since the primary path does not train the vision model, no vision training split is required. Keep an untouched independent evaluation subset. If fallback training is approved, split by scene before cropping and seal the test scenes.
5. Normalize/crop exactly as required by the selected pretrained checkpoint. Do not convert calibrated SAR values to arbitrary RGB or apply natural-image normalization without evidence.
6. Create a manifest with image count, scene count, label counts, dimensions, bands/channels, nodata treatment, timestamps/coordinates availability, hash, source, and storage consumed.
7. Add data loaders and validation scripts; do not store raw imagery in Git. Add appropriate local data paths to `.gitignore` while keeping small manifests/examples tracked.

Expected outputs:

- `data/raw/sar/<selected-dataset>/` (local only, small subset; do not download both by default)
- `data/processed/sar/chips/` (local only)
- `data/processed/sar/evaluation_manifest.csv` (or equivalent, containing only the evaluation subset and provenance; do not create training splits in the pretrained-only path)
- `reports/data_acquisition_manifest.md`
- A tested dataset reader and annotation-conversion utility.

## 7. Phase C — Detector baselines and evaluation

1. Implement a stable adapter around the selected pretrained detector and its official preprocessing/inference code. Keep upstream code attribution and license notices.
2. Run inference on a small pilot and inspect outputs visually alongside annotations. Verify georeferencing, channel order, scale, image orientation, and box coordinates. Save a review montage.
3. Evaluate the selected checkpoint on a verified independent subset. If provenance overlaps planned xView3 test scenes, do not report those results as independent; use a compatible external dataset or choose a different checkpoint/split.
4. Use a second dataset only for a defined cross-dataset diagnostic, and clearly state the domain/label differences. It is optional.
5. Use official xView3 metrics/code where feasible for xView3; for HRSID use appropriate object detection metrics. Report precision, recall, F1, AP/mAP at stated IoU thresholds, false positives per image, inference latency, and confidence intervals or per-scene variation where practical. Do not compare metrics computed under different matching rules as if they were directly equivalent.
6. Keep evaluation separate from the existing synthetic ablation. Label outputs, tables, and plots with dataset and split provenance.
7. Default to pretrained inference with no vision training. If the baseline cannot run or has a documented severe mismatch, record the issue and propose the smallest fallback adaptation. Do not start an expensive run without reporting its expected resource use and getting the owner's go-ahead. Never tune on the sealed test set.

Potential detector implementation options:

- Published xView3 solution weights for Sentinel-1 vessel detection, subject to license/provenance and current download availability: <https://github.com/allenai/sar_vessel_detect>
- Official xView3 reference implementation: <https://github.com/DIUx-xView/xview3-reference>
- HRSID Faster R-CNN checkpoint candidate; independently validate quality, code compatibility, and license: <https://huggingface.co/PUSHPENDAR/hrsid-ship-detection>

Do not assume Ultralytics YOLO is the best immediate detector. Use it only if annotations convert reliably and a fair baseline can be measured. xView3 uses large multichannel SAR scenes and challenge-specific detection/characterization rules; reusing an established compatible model can save substantial integration and training effort.

## 8. Phase D — Real image-derived features and AIS fusion

1. Add a typed SAR image detection record with at least source scene, image ID, timestamp, coordinate/CRS, pixel coordinates, geospatial coordinates if available, box/mask, detector confidence, sensor/polarization, pixel scale, and provenance.
2. Convert detections into existing SAR schema only when units and semantics match. Keep pixel sizes separate from meters. Derive physical dimensions only when reliable pixel spacing or annotation metadata supports conversion; otherwise mark unavailable.
3. Add image-derived measurements only when actual pixels support them: pixel area, local intensity/backscatter statistics, contrast, shape, orientation, and detection confidence. Document calibration/normalization and do not call a derived quantity RCS unless the data and calibration justify it.
4. Match SAR detections with AIS using scene acquisition time, coordinates, a documented spatial/time gate, and vessel motion uncertainty. Store candidate matches and offsets, not only a yes/no result. Test sensitivity to match tolerances.
5. Represent labels conservatively: `AIS_MATCHED`, `AIS_UNMATCHED`, `AMBIGUOUS`, or `INSUFFICIENT_COVERAGE` as appropriate. Do not convert all unmatched detections into confirmed dark-vessel truth.
6. Use the existing feature pipeline and risk scorer after checking their assumptions and units. Keep `risk_score` terminology unless a score has been calibrated on valid labeled data.
7. Add fixtures from a few public samples only when redistribution is allowed; otherwise tests should use small generated test arrays and mocked metadata, while real-data paths remain opt-in.

Required evaluation:

- Detector metrics against image annotations.
- SAR-AIS association precision/recall only where trustworthy association labels exist.
- Risk-score analysis separated into heuristic sensitivity and predictive performance. Do not compute predictive metrics against labels generated from the same risk rules.
- Error review: missed ships, false detections, uncertain AIS matches, coastal clutter, small craft, and source coverage gaps.

## 9. Phase E — LLM fine-tuning and grounded reporting

The LLM is separate from the SAR detector and risk scorer. Its role is to explain and format already computed evidence, identify missing evidence, answer analyst questions over case evidence, and propose human-reviewed follow-up steps. It must not calculate distances, SAR physics, legal conclusions, or authoritative citations from memory.

### First: repair the data and evaluation design

1. Audit `training/build_dataset.py`, current JSONL files, and `training/evaluate.py` for circular labels, train/validation overlap, label leakage, and prompt-template memorization.
2. Existing 50/15 deterministic examples may be used to validate code only. Do not present them as independent evidence of model quality.
3. Build a versioned instruction dataset from real pipeline outputs plus independently written/analyst-reviewed target reports. Include normal, AIS-matched, unmatched/ambiguous, sanctions hit/no hit, degraded sources, small craft, uncertainty, and abstention cases. Store provenance and author/reviewer/source metadata. Never expose restricted personal, account, or API credentials.
4. Aim initially for 150–300 diverse, reviewed examples if time permits; prioritize quality and scenario diversity over synthetic count. Keep case families/scenes split between train and validation/test so near-duplicate cases do not cross splits.
5. Validate cited law/reference facts using primary official documents and retrieval; fine-tuning alone does not guarantee correct or “zero hallucination” citations.

### Model choice and run

- Start with `Qwen/Qwen2.5-1.5B-Instruct` QLoRA only if GPU/VRAM and package compatibility checks pass; otherwise use 0.5B for a pipeline smoke test and use a compatible cloud GPU for the substantive run. Consider 3B only if measured GPU memory allows it.
- The project already has a training script, but verify the current Transformers/TRL/PEFT APIs, assistant-only loss masking, chat-template formatting, checkpoint resume, and adapter save/load before training.
- Run base-model prompting and fine-tuned inference on the exact same held-out cases and decoding settings.
- Keep at least one base-vs-adapter comparison. Report JSON/Pydantic validity, required-field completeness, evidence fidelity, unsupported-claim rate, correct abstention under degradation, citation validity, task/classification accuracy if applicable, latency, and memory. Human review is useful for report quality. Do not claim zero hallucinations from a small benchmark.
- Do not train a SAR image model and the LLM in one job. They have different inputs, objectives, datasets, libraries, and metrics.

## 10. Phase F — Agent integration and end-to-end demo

1. Extend the existing graph so the SAR detection/import step is represented as a traceable node/tool with typed inputs/outputs. Preserve the current deterministic nodes and risk engine.
2. Add nodes/tools for AIS correlation with explicit ambiguous/coverage states, report synthesis (if LLM adapter is available), schema validation, citation/evidence validation, and human review.
3. Keep high-risk or weakly supported findings gated for human review. Reports must distinguish measured facts, inferred matches, heuristic risk scores, source limitations, and recommendations.
4. Add an offline demo that can run on a small included/generated sample without downloading large datasets. Add an opt-in real-data demo that accepts local dataset paths and reports missing prerequisites clearly.
5. Demonstrate at least: clear AIS match, unmatched but uncertain AIS, high-risk heuristic scenario, small craft, sanctions match fixture, missing AIS feed, sanctions outage, and human-review pause/resume.
6. Save machine-readable traces and a rendered example report. Make it clear when a scenario uses fixtures rather than real-world data.

## 11. Phase G — Final verification, documentation, and handoff

1. Run the complete tests and every documented demo from a fresh environment if feasible. Record command, exit code, duration, dependency versions, and machine details.
2. Run data-manifest checks and verify additional working storage remains below 15 GB, targeting under 10 GB.
3. Confirm no secrets, raw datasets, model weights, caches, credentials, or large generated outputs are staged for Git. Do not commit external datasets or model artifacts unless repository policy explicitly permits and files are appropriately small/licensed.
4. Update README, roadmap, architecture, data sources, and audit reports. Remove unsupported statements such as “real 35,000 Sentinel-1 detections,” “real 103,120 AIS pings,” “court-admissible,” “zero hallucination,” or “fine-tuning complete” unless evidence now supports the specific claim.
5. Keep old synthetic benchmark results but label their generator, seed, and synthetic status. Never merge them with real-data metrics without explicit labels.
6. Provide a concise final report with:
   - completed/not completed per phase;
   - exact datasets, versions, licenses, scene IDs, splits, and bytes used;
   - detector checkpoint and provenance;
   - actual measured metrics and exact evaluation commands;
   - whether vision training happened and whether LLM training happened;
   - adapter location and size if training succeeded;
   - known limitations and failed attempts;
   - steps to reproduce the demo on another machine.
7. Do not commit, push, publish, upload, or send project data anywhere unless the human owner explicitly asks. Preserve all existing local user changes.

## 12. Storage plan and cleanup rules

At each phase, report the actual total bytes used. Keep data under `data/raw/` and `data/processed/`, and model caches/checkpoints in explicit project paths. Set framework cache environment variables to a project-local cache directory before model downloads where practical.

Suggested checkpoints policy:

- Retain the selected published detector checkpoint, one final LLM adapter if training succeeds, tokenizer/config files, and small evaluation outputs.
- Delete only reproducible intermediate chips/caches/checkpoints after checking the manifest and confirming the retained source/outputs are adequate.
- Do not delete the only source copy, original annotations, or final model without human instruction.
- Stop downloads/training before exceeding 15 GB additional storage; report measured sizes and the smallest useful subset if the cap is approached.

## 13. Time estimate

These are planning ranges, not guarantees. Report observed time per operation and update the estimate after preflight.

| Work | Estimated active time |
|---|---:|
| Host preflight, dependency setup, existing verification | 1–4 hours |
| Data access, pilot download, license/provenance checks | 1–4 hours, plus network wait |
| Small subset download/extraction/annotation conversion | 1–5 hours, depending on access and bandwidth |
| Pretrained detector integration and pilot inference | 2–6 hours |
| Metrics, error analysis, and real-data feature/AIS integration | 1–3 days |
| Optional vision adaptation, only if required | 2–12 GPU hours plus setup/debugging; excluded from primary path |
| LLM dataset audit and QLoRA experiment | 3–12 GPU hours plus setup/debugging |
| Agent/demo/documentation integration and final reproduction | 1–2 days |

Expected project duration: approximately **2–5 focused workdays** after data access and a working environment are available. Actual elapsed time depends on source access, network speed, GPU, and package compatibility. The primary path avoids SAR detector training; the only planned training run is the separate LLM QLoRA experiment, and it should proceed only if the hardware check supports it.

## 14. Required final status vocabulary

Use these labels in final reports:

- **IMPLEMENTED AND REPRODUCED** — command was run successfully in the current environment and artifact exists.
- **IMPLEMENTED, NOT REPRODUCED HERE** — code exists but current environment could not run it.
- **PRETRAINED CHECKPOINT INFERRED** — inference used downloaded existing weights; no project vision training implied.
- **FINE-TUNED AND EVALUATED** — training completed, adapter/checkpoint exists, held-out metrics were generated.
- **SYNTHETIC DEMONSTRATION** — generated data/labels, never real-world validation.
- **BLOCKED** — specific external/hardware/data issue prevented execution.
- **PLANNED** — not implemented.

## 15. Primary references to verify during execution

Use primary dataset/model repositories and papers for current download instructions, data schemas, license/terms, and checkpoint provenance. Recheck pages at execution time because links and access policies may change.

- xView3 challenge paper/dataset: <https://arxiv.org/abs/2206.00897>
- xView3 official/reference repository: <https://github.com/DIUx-xView/xview3-reference>
- xView3 winning solutions: <https://github.com/DIUx-xView>
- AI2/Skylight detector implementation and weights: <https://github.com/allenai/sar_vessel_detect>
- HRSID data, annotations, and terms: <https://github.com/chaozhong2010/HRSID>
- HRSID paper: <https://www.mdpi.com/2072-4292/13/18/3690>
- Candidate HRSID checkpoint: <https://huggingface.co/PUSHPENDAR/hrsid-ship-detection>
- GFW API: <https://globalfishingwatch.org/our-apis/documentation/>
- NOAA AccessAIS: <https://marinecadastre.gov/accessais/>
- Qwen2.5 model family: <https://huggingface.co/collections/Qwen/qwen25>

This roadmap is an implementation brief, not proof that downloads, training, or real-world performance have already occurred.
