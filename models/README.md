# Maritime Intelligence Models & Weights

This directory holds weights, checkpoints, and configurations for the neural detection and language model components of the maritime intelligence pipeline.

> [!NOTE]
> In accordance with repository standards, large model binary weights (`*.pt`, `*.safetensors`, `*.bin`, etc.) are excluded from Git version control. Follow the instructions below to acquire, download, or train the models.

---

## 1. Directory Structure

```
models/
├── README.md
├── sar_detector/
│   └── unquantized/
│       └── best.pt                  # YOLOv8 SAR vessel detection neural weights
└── maritime_qwen_adapter/
    ├── adapter_config.json          # PEFT LoRA configuration
    ├── adapter_model.safetensors    # 16-bit LoRA adapter weights (73.9 MB)
    └── tokenizer_config.json
```

---

## 2. Obtaining Model Artifacts

### Option A: Local Reproduction (Recommended)

1. **SAR Vessel Detector (YOLOv8-SAR)**:
   The lightweight SAR vessel detector network (~6 MB) can be initialized or trained directly on Sentinel-1 radar chips:
   ```bash
   python scripts/run_real_satellite_agent_demo.py
   ```

2. **Maritime Qwen 2.5 LoRA Adapter**:
   Train the 16-bit LoRA adapter locally across 57 optimization steps using the fine-tuning pipeline:
   ```bash
   python training/train_qlora.py --model_id Qwen/Qwen2.5-1.5B-Instruct --epochs 3 --output_dir models/maritime_qwen_adapter
   ```

3. **Standalone Merged Model**:
   Export and merge the LoRA weights into a self-contained, unquantized model folder:
   ```bash
   python scripts/export_merged_model.py
   ```

### Option B: External Model Distribution

When distributing models across teams or deploying to production environments without retraining:
* **Hugging Face Hub**: Hosted at `https://huggingface.co/Phonicxxxx24/maritime-qwen-adapter`.
* **GitHub Releases**: Download `maritime_qwen_adapter.tar.gz` and `best.pt` from the repository's GitHub Releases tab and extract into `models/`.
