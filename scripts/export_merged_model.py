"""Exports the fine-tuned PEFT LoRA adapter merged into the base Qwen2.5-1.5B-Instruct model.
This produces a standalone, self-contained model folder that can run anywhere
(including on home PCs without GPUs, without requiring PEFT hooks at runtime).
"""

import os
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

BASE_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
ADAPTER_PATH = "models/maritime_qwen_adapter"
MERGED_OUTPUT_PATH = "models/maritime_qwen_merged"

def merge_and_export():
    if not os.path.exists(ADAPTER_PATH):
        raise FileNotFoundError(
            f"LoRA adapter directory '{ADAPTER_PATH}' not found. "
            "Please train the adapter with 'python training/train_qlora.py' or refer to models/README.md."
        )
    print(f"Loading base model: {BASE_MODEL}...")
    tokenizer = AutoTokenizer.from_pretrained(ADAPTER_PATH)
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=dtype,
        device_map=device
    )
    
    print(f"Loading and applying LoRA adapter from: {ADAPTER_PATH}...")
    peft_model = PeftModel.from_pretrained(base_model, ADAPTER_PATH)
    
    print("Merging adapter weights into base model weights...")
    merged_model = peft_model.merge_and_unload()
    
    os.makedirs(MERGED_OUTPUT_PATH, exist_ok=True)
    print(f"Saving merged standalone model to: {MERGED_OUTPUT_PATH}...")
    merged_model.save_pretrained(MERGED_OUTPUT_PATH, safe_serialization=True)
    tokenizer.save_pretrained(MERGED_OUTPUT_PATH)
    print("Export complete! The model can now run standalone without GPU or PEFT dependencies.")

if __name__ == "__main__":
    merge_and_export()
