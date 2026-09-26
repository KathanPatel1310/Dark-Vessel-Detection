# Pillar 3: Maritime Intelligence LLM Fine-Tuning (QLoRA)

This directory implements the parameter-efficient supervised fine-tuning (SFT) pipeline for specialized maritime intelligence bulletin synthesis.

---

## 1. Directory Structure

```
training/
├── README.md                     # Technical guide and procedure specification
├── build_dataset.py              # Deterministic dataset generation script
├── train_qlora.py                # PEFT/TRL QLoRA training script
├── evaluate.py                   # Quantitative evaluation and schema conformance benchmark
└── data/
    ├── maritime_train.jsonl      # 50 training instruction pairs
    └── maritime_validation.jsonl # 15 held-out validation instruction pairs
```

---

## 2. Dataset Design & Format

Datasets are generated in standard Hugging Face Chat JSONL format, compatible with Qwen 2.5 chat templates:

```json
{
  "id": "MAR-SFT-0001",
  "scenario_type": "DELIBERATE_DARK_EVASION",
  "messages": [
    {
      "role": "system",
      "content": "You are an expert maritime intelligence analyst..."
    },
    {
      "role": "user",
      "content": "ANALYZE MARITIME TARGET TELEMETRY:\n- Target Detection ID: SAR-DARK-001\n..."
    },
    {
      "role": "assistant",
      "content": "{\n  \"report_id\": \"MAR-INTEL-20260920-DARK-001\",\n  \"threat_tier\": \"SEVERE\",\n  \"statutory_violations\": [...],\n  ...\n}"
    }
  ],
  "ground_truth_metadata": { ... }
}
```

### Scenario Coverage Matrix
1. **`NORMAL_CORRELATED`**: Commercial vessels transmitting valid AIS matching radar dimensions.
2. **`DELIBERATE_DARK_EVASION`**: Large commercial hulls (> 100m) running dark in international waters.
3. **`SANCTIONED_VESSEL`**: Targets matched to official OFAC SDN / UN Consolidated watchlists.
4. **`AIS_GAP_SUSPICIOUS`**: Vessels with prolonged transponder outages near EEZs or STS zones.
5. **`DEGRADED_EVIDENCE`**: Scenarios simulating sensor outages, missing AIS, or unavailable registries.
6. **`SMALL_CRAFT_EXEMPT`**: Small coastal craft (< 30m) legally exempt under SOLAS Chapter V Reg. 19.

---

## 3. Scaling Path

- **Initial Bootstrap**: 50 training + 15 validation reproducible examples generated from project fixtures and mathematical pipelines.
- **Scale to 400+ Examples**: Run `python training/build_dataset.py` with parameter `--train_count 400 --val_count 80`. The generator uses real geospatial points and varies coordinate seeds, hull aspect ratios, and clutter conditions across the Arabian Sea.

---

## 4. Hardware Targets & Models

| Tier | Model ID | Target Hardware | Quantization | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Local Experimentation** | `Qwen/Qwen2.5-0.5B-Instruct` | CPU or Laptop GPU | FP16 / FP32 | Supported |
| **Edge / Fast SFT** | `Qwen/Qwen2.5-1.5B-Instruct` | 6GB VRAM GPU (RTX 4050/3060) | FP16 / 4-bit | Supported |
| **Production Target (Tier 1)** | `Qwen/Qwen2.5-3B-Instruct` | 8GB–12GB VRAM GPU / Colab T4 | 4-bit QLoRA | Planned Target |
| **Production Target (Tier 2)** | `Qwen/Qwen2.5-7B-Instruct` | 16GB+ VRAM GPU / A100 | 4-bit QLoRA | Planned Target |

---

## 5. Execution Commands

### Step 1: Generate Datasets
```bash
python training/build_dataset.py
```

### Step 2: Validate Prerequisites & Dry Run
```bash
python training/train_qlora.py --no_4bit --dry_run
```

### Step 3: Run Fine-Tuning (When Ready)
- **On Local GPU (without bitsandbytes)**:
  ```bash
  python training/train_qlora.py --model_id Qwen/Qwen2.5-0.5B-Instruct --no_4bit --epochs 3
  ```
- **On Linux / Colab GPU (with 4-bit QLoRA)**:
  ```bash
  python training/train_qlora.py --model_id Qwen/Qwen2.5-3B-Instruct --epochs 3
  ```

### Step 4: Run Evaluation Benchmark
```bash
python training/evaluate.py --reference_baseline
```
