"""QLoRA Supervised Fine-Tuning Script for Maritime Intelligence (Pillar 3).
Fine-tunes open-weight instruction models (Qwen 2.5 family) on domain-specific
maritime surveillance bulletins using parameter-efficient Low-Rank Adaptation (LoRA)
and 4-bit quantization via bitsandbytes and Hugging Face TRL.

Hardware Targets:
- Production/Colab: Qwen/Qwen2.5-7B-Instruct or Qwen/Qwen2.5-3B-Instruct (4-bit QLoRA)
- Local Experimentation: Qwen/Qwen2.5-0.5B-Instruct or Qwen/Qwen2.5-1.5B-Instruct
"""

import argparse
import os
import sys
from typing import Dict, Any

import torch
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
)
from peft import LoraConfig, get_peft_model, TaskType


def check_prerequisites(use_4bit: bool = True) -> Dict[str, Any]:
    """
    Validates hardware and library requirements. Fails helpfully and clearly
    if CUDA or bitsandbytes is unavailable.
    """
    cuda_available = torch.cuda.is_available()
    device_name = torch.cuda.get_device_name(0) if cuda_available else "CPU (No CUDA)"
    
    bnb_available = False
    try:
        import bitsandbytes # noqa: F401
        bnb_available = True
    except ImportError:
        pass

    print("=" * 60)
    print("ENVIRONMENT PRE-FLIGHT CHECK")
    print(f"  - PyTorch Version   : {torch.__version__}")
    print(f"  - CUDA Available    : {cuda_available} ({device_name})")
    print(f"  - bitsandbytes      : {'Available' if bnb_available else 'Not Installed'}")
    print(f"  - 4-bit Quantization: {'Requested' if use_4bit else 'Disabled'}")
    print("=" * 60)

    if use_4bit:
        if not cuda_available:
            print("\n[ERROR: CUDA Required for 4-bit QLoRA]")
            print("4-bit quantization via bitsandbytes requires an active NVIDIA CUDA GPU.")
            print("To run on CPU for local development/testing, pass `--no_4bit`.")
            print("To train on GPU, run this script in an environment with CUDA enabled (e.g. Google Colab / Linux GPU server).\n")
            sys.exit(1)

        if not bnb_available:
            print("\n[ERROR: bitsandbytes Required for 4-bit Quantization]")
            print("Package 'bitsandbytes' is required for 4-bit NF4/FP4 quantization.")
            print("Install via: pip install bitsandbytes")
            print("Note: On Windows, install via pre-compiled wheel or run on Linux/Colab.")
            print("Alternatively, pass `--no_4bit` to train with standard 16-bit or 32-bit LoRA.\n")
            sys.exit(1)

    return {
        "cuda_available": cuda_available,
        "bnb_available": bnb_available,
        "device": "cuda" if cuda_available else "cpu"
    }


def format_chat_prompt(batch: Dict[str, Any], tokenizer) -> Dict[str, Any]:
    """Formats conversation turns into model-specific chat template tokens."""
    formatted_texts = []
    for messages in batch["messages"]:
        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=False
        )
        formatted_texts.append(text)
    return {"text": formatted_texts}


def run_training(
    model_id: str,
    train_path: str,
    val_path: str,
    output_dir: str,
    use_4bit: bool = True,
    epochs: int = 3,
    batch_size: int = 2,
    lr: float = 2e-4,
    dry_run: bool = False
):
    """Executes the QLoRA / LoRA fine-tuning pipeline using TRL SFTTrainer."""
    env = check_prerequisites(use_4bit=use_4bit)

    if not os.path.exists(train_path):
        raise FileNotFoundError(f"Training dataset not found at: {train_path}. Run `python training/build_dataset.py` first.")

    print(f"\n[1/5] Loading datasets from: {train_path}")
    raw_datasets = load_dataset("json", data_files={"train": train_path, "validation": val_path})
    print(f"  Loaded {len(raw_datasets['train'])} train examples, {len(raw_datasets['validation'])} validation examples.")

    print(f"\n[2/5] Initializing Tokenizer: {model_id}")
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    if dry_run:
        print("\n[DRY RUN MODE]: Dataset and Tokenizer verified successfully. Exiting before model download.")
        return

    print(f"\n[3/5] Loading Foundation Model: {model_id}")
    model_kwargs = {
        "trust_remote_code": True,
        "device_map": "auto" if env["cuda_available"] else None
    }

    if use_4bit and env["cuda_available"] and env["bnb_available"]:
        from transformers import BitsAndBytesConfig
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True
        )
        model_kwargs["quantization_config"] = bnb_config
    elif not env["cuda_available"]:
        model_kwargs["torch_dtype"] = torch.float32

    model = AutoModelForCausalLM.from_pretrained(model_id, **model_kwargs)

    print("\n[4/5] Configuring LoRA Adapter")
    peft_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type=TaskType.CAUSAL_LM
    )
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()

    print(f"\n[5/5] Configuring Training Arguments -> {output_dir}")
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=4,
        learning_rate=lr,
        logging_steps=5,
        save_strategy="epoch",
        evaluation_strategy="epoch",
        fp16=env["cuda_available"],
        bf16=False,
        report_to="none"
    )

    try:
        from trl import SFTTrainer
        trainer = SFTTrainer(
            model=model,
            train_dataset=raw_datasets["train"],
            eval_dataset=raw_datasets["validation"],
            peft_config=peft_config,
            dataset_text_field="messages",
            max_seq_length=1024,
            tokenizer=tokenizer,
            args=training_args
        )
        print("\nStarting Training Run...")
        trainer.train()
        print(f"\nTraining Complete. Saving LoRA adapter to {output_dir}...")
        trainer.model.save_pretrained(output_dir)
        tokenizer.save_pretrained(output_dir)
        print(f"Adapter saved successfully to: {output_dir}")
    except Exception as e:
        print(f"\n[ERROR during training]: {e}")
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="QLoRA Fine-Tuning for Maritime Intelligence")
    parser.add_argument("--model_id", type=str, default="Qwen/Qwen2.5-0.5B-Instruct",
                        help="Base model ID (e.g. Qwen/Qwen2.5-0.5B-Instruct for testing, Qwen/Qwen2.5-7B-Instruct for production)")
    parser.add_argument("--train_data", type=str, default="training/data/maritime_train.jsonl")
    parser.add_argument("--val_data", type=str, default="training/data/maritime_validation.jsonl")
    parser.add_argument("--output_dir", type=str, default="models/maritime_qwen_adapter")
    parser.add_argument("--no_4bit", action="store_true", help="Disable 4-bit quantization (run in fp16 or fp32)")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch_size", type=int, default=2)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--dry_run", action="store_true", help="Validate prerequisites and dataset without training")
    args = parser.parse_args()

    run_training(
        model_id=args.model_id,
        train_path=args.train_data,
        val_path=args.val_data,
        output_dir=args.output_dir,
        use_4bit=not args.no_4bit,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        dry_run=args.dry_run
    )
