#!/usr/bin/env python3
"""Build a tiny BERT-style model artifact for Hugging Face deployment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from transformers import BertConfig, BertModel, BertTokenizerFast


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create TinyModel1 files under artifacts/ for HF upload."
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts/TinyModel1",
        help="Output directory where model/tokenizer files are saved.",
    )
    return parser.parse_args()


def write_vocab(vocab_path: Path) -> None:
    base_tokens = ["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]"]
    domain_tokens = [
        "tiny",
        "model",
        "base",
        "fast",
        "small",
        "efficient",
        "token",
        "embedding",
        "transformer",
        "attention",
        "adapter",
        "inference",
        "latency",
        "accuracy",
        "deploy",
        "github",
        "hugging",
        "face",
        "artifact",
        "train",
        "eval",
    ]
    filler_tokens = [f"token_{i}" for i in range(0, 230)]
    all_tokens = base_tokens + domain_tokens + filler_tokens
    vocab_path.write_text("\n".join(all_tokens) + "\n", encoding="utf-8")


def write_model_card(readme_path: Path) -> None:
    readme = """---
license: apache-2.0
library_name: transformers
tags:
  - tiny
  - bert
  - base-model
  - experimental
---

# TinyModel1

TinyModel1 is a compact BERT-style encoder intended as a starting point for
rapid experimentation, adapter research, and quick deployment demos.

## Intended use

- Base checkpoint for continued pretraining or task-specific finetuning
- Testbed for parameter-efficient methods (LoRA/adapters/quantization)
- CI-friendly artifact for end-to-end HF deploy validation

## Architecture

- Model type: BERT encoder (`BertModel`)
- Hidden size: 128
- Layers: 2
- Attention heads: 4
- Intermediate size: 256
- Vocab size: 256

## Notes

This checkpoint is randomly initialized and not pretrained on large corpora.
Use it as a foundation artifact and evolve it in future iterations.
"""
    readme_path.write_text(readme, encoding="utf-8")


def write_artifact_manifest(path: Path) -> None:
    data = {
        "name": "TinyModel1",
        "version": "0.1.0",
        "framework": "transformers",
        "model_class": "BertModel",
        "purpose": "base-for-latest-developments",
    }
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    vocab_path = output_dir / "vocab.txt"
    write_vocab(vocab_path)

    tokenizer = BertTokenizerFast(
        vocab_file=str(vocab_path),
        unk_token="[UNK]",
        sep_token="[SEP]",
        pad_token="[PAD]",
        cls_token="[CLS]",
        mask_token="[MASK]",
    )
    tokenizer.save_pretrained(output_dir)

    config = BertConfig(
        vocab_size=256,
        hidden_size=128,
        num_hidden_layers=2,
        num_attention_heads=4,
        intermediate_size=256,
        max_position_embeddings=256,
        type_vocab_size=2,
        pad_token_id=0,
    )
    model = BertModel(config)
    model.save_pretrained(output_dir, safe_serialization=True)

    write_model_card(output_dir / "README.md")
    write_artifact_manifest(output_dir / "artifact.json")
    print(f"TinyModel1 artifact written to: {output_dir}")


if __name__ == "__main__":
    main()
