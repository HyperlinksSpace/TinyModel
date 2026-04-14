#!/usr/bin/env python3
"""Train TinyModel1 on AG News and export HF artifact files."""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from datasets import load_dataset
from tokenizers import Tokenizer
from tokenizers.models import WordPiece
from tokenizers.normalizers import Lowercase, NFD, Sequence, StripAccents
from tokenizers.pre_tokenizers import Whitespace
from tokenizers.trainers import WordPieceTrainer
from torch.utils.data import DataLoader
from transformers import (
    BertConfig,
    BertForSequenceClassification,
    BertTokenizerFast,
    DataCollatorWithPadding,
)


LABELS = ["World", "Sports", "Business", "Sci/Tech"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train TinyModel1 from scratch on AG News."
    )
    parser.add_argument("--output-dir", default="artifacts/TinyModel1")
    parser.add_argument("--max-train-samples", type=int, default=6000)
    parser.add_argument("--max-eval-samples", type=int, default=1200)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--vocab-size", type=int, default=8000)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


@dataclass
class TrainState:
    train_loss: float
    eval_accuracy: float


def build_tokenizer(texts: list[str], vocab_size: int, output_dir: Path) -> BertTokenizerFast:
    tokenizer_model = Tokenizer(WordPiece(unk_token="[UNK]"))
    tokenizer_model.normalizer = Sequence([NFD(), Lowercase(), StripAccents()])
    tokenizer_model.pre_tokenizer = Whitespace()
    trainer = WordPieceTrainer(
        vocab_size=vocab_size,
        special_tokens=["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]"],
    )
    tokenizer_model.train_from_iterator(texts, trainer=trainer)
    tokenizer_path = output_dir / "tokenizer.json"
    tokenizer_model.save(str(tokenizer_path))

    tokenizer = BertTokenizerFast(
        tokenizer_file=str(tokenizer_path),
        unk_token="[UNK]",
        sep_token="[SEP]",
        pad_token="[PAD]",
        cls_token="[CLS]",
        mask_token="[MASK]",
    )
    tokenizer.save_pretrained(output_dir)
    return tokenizer


def write_model_card(path: Path, state: TrainState, args: argparse.Namespace) -> None:
    readme = f"""---
license: apache-2.0
library_name: transformers
datasets:
  - ag_news
tags:
  - tiny
  - text-classification
  - ag-news
---

# TinyModel1

TinyModel1 is a lightweight news-topic classifier trained from scratch on `ag_news`.

## Task

Input: short news text  
Output labels: World, Sports, Business, Sci/Tech

## Training setup

- Base model: tiny BERT from scratch
- Train samples: {args.max_train_samples}
- Eval samples: {args.max_eval_samples}
- Epochs: {args.epochs}
- Batch size: {args.batch_size}
- Learning rate: {args.learning_rate}

## Quick metrics

- Eval accuracy: {state.eval_accuracy:.4f}
- Final train loss: {state.train_loss:.4f}

## Intended use

- Fast baseline for category routing/classification
- Starter model for domain adaptation and production experiments
"""
    path.write_text(readme, encoding="utf-8")


def write_manifest(path: Path, state: TrainState) -> None:
    data = {
        "name": "TinyModel1",
        "version": "0.2.0",
        "task": "text-classification",
        "dataset": "ag_news",
        "base_model": "tinymodel1-bert-scratch",
        "labels": LABELS,
        "eval_accuracy": round(state.eval_accuracy, 4),
        "train_loss": round(state.train_loss, 4),
    }
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def evaluate(
    model: BertForSequenceClassification,
    loader: DataLoader,
    device: torch.device,
) -> float:
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for batch in loader:
            labels = batch.pop("labels").to(device)
            batch = {k: v.to(device) for k, v in batch.items()}
            logits = model(**batch).logits
            preds = torch.argmax(logits, dim=-1)
            correct += (preds == labels).sum().item()
            total += labels.shape[0]
    return correct / max(1, total)


def main() -> None:
    args = parse_args()
    set_seed(args.seed)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ds = load_dataset("ag_news")
    train_ds = ds["train"].shuffle(seed=args.seed).select(range(args.max_train_samples))
    eval_ds = ds["test"].shuffle(seed=args.seed).select(range(args.max_eval_samples))

    tokenizer = build_tokenizer(train_ds["text"], args.vocab_size, output_dir)
    config = BertConfig(
        vocab_size=tokenizer.vocab_size,
        hidden_size=128,
        num_hidden_layers=2,
        num_attention_heads=4,
        intermediate_size=256,
        max_position_embeddings=256,
        type_vocab_size=2,
        pad_token_id=tokenizer.pad_token_id,
        num_labels=4,
        id2label={i: label for i, label in enumerate(LABELS)},
        label2id={label: i for i, label in enumerate(LABELS)},
    )
    model = BertForSequenceClassification(config)

    def tokenize(batch: dict[str, list[str]]) -> dict[str, list[int]]:
        return tokenizer(batch["text"], truncation=True, max_length=128)

    train_ds = train_ds.map(tokenize, batched=True)
    eval_ds = eval_ds.map(tokenize, batched=True)
    train_ds = train_ds.rename_column("label", "labels")
    eval_ds = eval_ds.rename_column("label", "labels")
    train_ds.set_format(type="torch", columns=["input_ids", "attention_mask", "labels"])
    eval_ds.set_format(type="torch", columns=["input_ids", "attention_mask", "labels"])

    collator = DataCollatorWithPadding(tokenizer=tokenizer)
    train_loader = DataLoader(
        train_ds,
        batch_size=args.batch_size,
        shuffle=True,
        collate_fn=collator,
    )
    eval_loader = DataLoader(
        eval_ds,
        batch_size=args.batch_size,
        shuffle=False,
        collate_fn=collator,
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate)

    model.train()
    last_loss = 0.0
    for epoch in range(args.epochs):
        running_loss = 0.0
        steps = 0
        for batch in train_loader:
            labels = batch.pop("labels").to(device)
            batch = {k: v.to(device) for k, v in batch.items()}

            out = model(**batch, labels=labels)
            loss = out.loss
            loss.backward()
            optimizer.step()
            optimizer.zero_grad(set_to_none=True)

            running_loss += loss.item()
            steps += 1
        last_loss = running_loss / max(1, steps)
        print(f"epoch={epoch + 1} train_loss={last_loss:.4f}")

    accuracy = evaluate(model, eval_loader, device)
    print(f"eval_accuracy={accuracy:.4f}")

    model.save_pretrained(output_dir, safe_serialization=True)
    tokenizer.save_pretrained(output_dir)

    state = TrainState(train_loss=last_loss, eval_accuracy=accuracy)
    write_model_card(output_dir / "README.md", state, args)
    write_manifest(output_dir / "artifact.json", state)
    print(f"Saved TinyModel1 to: {output_dir}")


if __name__ == "__main__":
    main()
