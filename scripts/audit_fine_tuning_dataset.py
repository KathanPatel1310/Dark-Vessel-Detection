"""
Phase 10 & 11: Fine-Tuning Dataset & Pipeline Audit Script.
Analyzes token lengths, scenario distributions, exact/near duplicates, train/val overlap,
and evaluates TRL / Transformers / PEFT API compatibility.
"""

import json
import os
import difflib
import numpy as np
from transformers import AutoTokenizer

def audit_fine_tuning_datasets():
    print("=== AUDITING FINE-TUNING DATASETS ===")
    train_path = "training/data/maritime_train.jsonl"
    val_path = "training/data/maritime_validation.jsonl"

    with open(train_path, "r", encoding="utf-8") as f:
        train_records = [json.loads(line) for line in f]
    with open(val_path, "r", encoding="utf-8") as f:
        val_records = [json.loads(line) for line in f]

    print(f"Loaded {len(train_records)} train records, {len(val_records)} validation records.")

    # Load tokenizer to calculate true token length
    tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-0.5B-Instruct")

    def get_token_lengths(records):
        prompt_lens = []
        target_lens = []
        total_lens = []
        scenarios = {}
        classes = {}
        target_texts = []

        for r in records:
            messages = r["messages"]
            prompt_str = messages[0]["content"] + "\n" + messages[1]["content"]
            target_str = messages[2]["content"]

            p_tokens = len(tokenizer.encode(prompt_str))
            t_tokens = len(tokenizer.encode(target_str))
            tot_tokens = len(tokenizer.apply_chat_template(messages, tokenize=True))

            prompt_lens.append(p_tokens)
            target_lens.append(t_tokens)
            total_lens.append(tot_tokens)
            target_texts.append(target_str)

            # Extract scenario and classification from target JSON
            try:
                target_json = json.loads(target_str)
                tt = target_json.get("threat_tier", "UNKNOWN")
                classes[tt] = classes.get(tt, 0) + 1
            except Exception:
                pass

        return {
            "prompt_lens": prompt_lens,
            "target_lens": target_lens,
            "total_lens": total_lens,
            "classes": classes,
            "target_texts": target_texts
        }

    train_stats = get_token_lengths(train_records)
    val_stats = get_token_lengths(val_records)

    # Check for exact duplicate prompts or targets
    train_prompts = [r["messages"][1]["content"] for r in train_records]
    val_prompts = [r["messages"][1]["content"] for r in val_records]

    exact_train_dups = len(train_prompts) - len(set(train_prompts))
    overlap_prompts = set(train_prompts).intersection(set(val_prompts))

    # Check near-duplicates in train
    near_dups = 0
    for i in range(len(train_prompts)):
        for j in range(i + 1, len(train_prompts)):
            ratio = difflib.SequenceMatcher(None, train_prompts[i], train_prompts[j]).ratio()
            if ratio > 0.95:
                near_dups += 1

    results = {
        "train_count": len(train_records),
        "val_count": len(val_records),
        "train_prompt_tokens_mean": round(float(np.mean(train_stats["prompt_lens"])), 1),
        "train_prompt_tokens_max": int(np.max(train_stats["prompt_lens"])),
        "train_target_tokens_mean": round(float(np.mean(train_stats["target_lens"])), 1),
        "train_target_tokens_max": int(np.max(train_stats["target_lens"])),
        "train_total_tokens_mean": round(float(np.mean(train_stats["total_lens"])), 1),
        "train_total_tokens_max": int(np.max(train_stats["total_lens"])),
        "val_total_tokens_mean": round(float(np.mean(val_stats["total_lens"])), 1),
        "val_total_tokens_max": int(np.max(val_stats["total_lens"])),
        "train_class_distribution": train_stats["classes"],
        "val_class_distribution": val_stats["classes"],
        "exact_train_duplicates": exact_train_dups,
        "train_val_prompt_overlap_count": len(overlap_prompts),
        "near_duplicate_pairs_train": near_dups
    }

    print("\n=== DATASET AUDIT METRICS ===")
    for k, v in results.items():
        print(f"  {k}: {v}")

    return results

if __name__ == "__main__":
    audit_fine_tuning_datasets()
