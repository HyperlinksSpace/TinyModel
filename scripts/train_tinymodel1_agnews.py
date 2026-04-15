#!/usr/bin/env python3
"""Train TinyModel1 on AG News and export HF artifact files."""

from __future__ import annotations

import argparse
import json
import random
import shutil
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

# Bundled with the repo; copied into the HF artifact next to README.md for the model card banner.
MODEL_CARD_IMAGE = "TinyModel1Image.png"
_REPO_ROOT = Path(__file__).resolve().parent.parent


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
    parser.add_argument(
        "--github-repo-url",
        default="https://github.com/HyperlinksSpace/TinyModel",
        help="Source repo URL printed on the Hugging Face model card.",
    )
    parser.add_argument(
        "--hf-namespace",
        default="HyperlinksSpace",
        help="Hugging Face org/user for model/Space links on the model card.",
    )
    return parser.parse_args()


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


@dataclass
class TrainState:
    train_loss: float
    eval_accuracy: float
    num_parameters: int


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


def _model_card_banner_image_markdown(output_dir: Path, display_name: str) -> str:
    if not (output_dir / MODEL_CARD_IMAGE).is_file():
        return ""
    return f"""<div align="center">
  <img src="{MODEL_CARD_IMAGE}" alt="{display_name}" style="max-width: 100%; width: 100%; height: auto; display: block;" />
</div>

"""


def _links_markdown(args: argparse.Namespace, display_name: str) -> str:
    """GitHub repo and Space URLs for the model card (no link to this model repo — readers are already on it)."""
    ns = args.hf_namespace.strip()
    gh = args.github_repo_url.strip()
    space_repo = f"{display_name}Space"
    space_hub_url = f"https://huggingface.co/spaces/{ns}/{space_repo}"
    return f"""## Links

- **Source code (train & export):** [{gh}]({gh})
- **Live demo (Space):** [{space_repo}]({space_hub_url}) (canonical Hub URL; avoids unreliable `*.hf.space` links)
"""


def copy_model_card_image(output_dir: Path) -> bool:
    """Copy TinyModel1Image.png from repo root into the artifact folder for README embedding."""
    src = _REPO_ROOT / MODEL_CARD_IMAGE
    if not src.is_file():
        print(f"Note: optional model card image not found at {src}, skipping.")
        return False
    dst = output_dir / MODEL_CARD_IMAGE
    shutil.copy2(src, dst)
    print(f"Copied model card image to {dst}")
    return True


def write_model_card(path: Path, state: TrainState, args: argparse.Namespace) -> None:
    display_name = Path(args.output_dir).resolve().name
    out = Path(args.output_dir).resolve()
    params_m = state.num_parameters / 1_000_000.0
    banner = _model_card_banner_image_markdown(out, display_name)
    links_block = _links_markdown(args, display_name)

    readme = f"""---
license: apache-2.0
library_name: transformers
pipeline_tag: text-classification
datasets:
  - ag_news
language:
  - en
tags:
  - tiny
  - bert
  - text-classification
  - ag-news
---

{banner}# {display_name}

**{display_name}** is a compact **encoder** model for **news topic classification**, trained from scratch on the [AG News](https://huggingface.co/datasets/fancyzhx/ag_news) dataset. It targets fast CPU/GPU inference, simple deployment behind a router or API, and use as a **baseline** before larger or domain-specific models.

{links_block}

---

## Model summary

| Field | Value |
|:--|:--|
| **Task** | Text classification (single-label, 4 classes) |
| **Labels** | World, Sports, Business, Sci/Tech |
| **Architecture** | Tiny BERT-style encoder (`BertForSequenceClassification`) |
| **Parameters** | {state.num_parameters:,} (~{params_m:.2f}M) |
| **Max sequence length** | 128 tokens (training & inference) |
| **Framework** | [Transformers](https://github.com/huggingface/transformers) · Safetensors |

---

## Model overview

This release fits a **small footprint** so you can run batch or interactive classification without heavy GPUs. Training uses a WordPiece tokenizer fit on the training split and a shallow BERT stack suited to short news sentences.

### **Core capabilities**

- **Topic routing** — assign one of four coarse news categories for search, feeds, or moderation triage.
- **Low latency** — small parameter count keeps inference suitable for edge and serverless setups.
- **Fine-tuning base** — swap labels or add data for your domain while keeping the same architecture.

---

## Training

| Setting | Value |
|:--|:--|
| **Train samples** | {args.max_train_samples} |
| **Eval samples** | {args.max_eval_samples} |
| **Epochs** | {args.epochs} |
| **Batch size** | {args.batch_size} |
| **Learning rate** | {args.learning_rate} |
| **Optimizer** | AdamW |

---

## Evaluation

| Metric | Value |
|:--|:--|
| **Eval accuracy** | {state.eval_accuracy:.4f} |
| **Final train loss** | {state.train_loss:.4f} |

Metrics are computed on the held-out eval split configured above; treat them as a **sanity-check baseline**, not a production SLA.

---

## Getting started

### Inference with `transformers`

```python
from transformers import pipeline

clf = pipeline(
    "text-classification",
    model="{display_name}",  # or local path after save
    tokenizer="{display_name}",
    top_k=None,
)
text = "Markets rose after the central bank held rates steady."
print(clf(text))
```

Use `top_k=None` (or your Transformers version’s equivalent) to obtain scores for **all** labels. Replace `"{display_name}"` with your Hugging Face model id (for example `HyperlinksSpace/{display_name}`) when loading from the Hub.

---

## Training data

- **Dataset:** [fancyzhx/ag_news](https://huggingface.co/datasets/fancyzhx/ag_news) (4-class news topics).
- **Preprocessing:** tokenizer trained on training texts; sequences truncated to 128 tokens.

---

## Intended use

- Prototyping **routing**, **tagging**, and **dashboard** features over English news-style text.
- Teaching and benchmarking small-classification setups.
- Starting point for **domain adaptation** (finance, sports, etc.) with your own labels.

---

## Limitations

- **Accuracy** is modest by design; do not rely on it for high-stakes decisions without validation on your data.
- **English-oriented** news wording; other languages or social-style text may degrade.
- **Four fixed classes**; not suitable as a general-purpose language model.

---

## License

This model is released under the **Apache 2.0** license (see repository `LICENSE` where applicable).
"""
    path.write_text(readme, encoding="utf-8")


def write_manifest(path: Path, state: TrainState, args: argparse.Namespace) -> None:
    display_name = Path(args.output_dir).resolve().name
    data = {
        "name": display_name,
        "version": "0.2.0",
        "task": "text-classification",
        "dataset": "ag_news",
        "base_model": "tinymodel1-bert-scratch",
        "labels": LABELS,
        "eval_accuracy": round(state.eval_accuracy, 4),
        "train_loss": round(state.train_loss, 4),
        "num_parameters": state.num_parameters,
        "max_train_samples": args.max_train_samples,
        "max_eval_samples": args.max_eval_samples,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "learning_rate": args.learning_rate,
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


def resolve_device() -> torch.device:
    if not torch.cuda.is_available():
        return torch.device("cpu")
    try:
        major, minor = torch.cuda.get_device_capability(0)
        # Newer PyTorch builds can drop support for older cards like P100 (sm_60).
        if major < 7:
            name = torch.cuda.get_device_name(0)
            print(
                f"CUDA device '{name}' (sm_{major}{minor}) is unsupported by current "
                "PyTorch build; falling back to CPU."
            )
            return torch.device("cpu")
    except Exception as exc:
        print(f"Could not validate CUDA capability ({exc}); falling back to CPU.")
        return torch.device("cpu")
    return torch.device("cuda")


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

    device = resolve_device()
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

    num_parameters = int(sum(p.numel() for p in model.parameters()))

    model.save_pretrained(output_dir, safe_serialization=True)
    tokenizer.save_pretrained(output_dir)

    copy_model_card_image(output_dir)

    state = TrainState(train_loss=last_loss, eval_accuracy=accuracy, num_parameters=num_parameters)
    write_model_card(output_dir / "README.md", state, args)
    write_manifest(output_dir / "artifact.json", state, args)
    print(f"Saved TinyModel1 to: {output_dir}")


if __name__ == "__main__":
    main()
