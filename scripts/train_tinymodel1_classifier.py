#!/usr/bin/env python3
"""Train a TinyModel1 BERT-style text classifier from scratch on a Hugging Face dataset."""

from __future__ import annotations

import argparse
import json
import numbers
import random
import shutil
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from datasets import Dataset, DatasetDict, load_dataset
from tokenizers import Tokenizer
from tokenizers.models import WordPiece
from tokenizers.normalizers import Lowercase, NFD, Sequence, StripAccents
from tokenizers.pre_tokenizers import Whitespace
from tokenizers.trainers import WordPieceTrainer
import torch.nn as nn
from torch.utils.data import DataLoader
from transformers import (
    BertConfig,
    BertForSequenceClassification,
    BertTokenizerFast,
    DataCollatorWithPadding,
)

# Default human-readable labels for fancyzhx/ag_news (int labels 0–3).
AG_NEWS_LABELS = ["World", "Sports", "Business", "Sci/Tech"]

MODEL_CARD_IMAGE = "TinyModel1Image.png"
_REPO_ROOT = Path(__file__).resolve().parent.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Train a compact BERT-style classifier from scratch on any single-label "
            "text classification dataset on the Hugging Face Hub (default: AG News)."
        )
    )
    parser.add_argument("--output-dir", default="artifacts/TinyModel1")
    parser.add_argument(
        "--dataset",
        default="fancyzhx/ag_news",
        help="Hub dataset id (e.g. fancyzhx/ag_news, emotion, glue/sst2).",
    )
    parser.add_argument(
        "--dataset-config",
        default=None,
        help="Optional dataset configuration name (e.g. SST-2 for glue/sst2).",
    )
    parser.add_argument(
        "--train-split",
        default="train",
        help="Training split name.",
    )
    parser.add_argument(
        "--eval-split",
        default="test",
        help="Evaluation split name (use 'validation' if the dataset has no test split).",
    )
    parser.add_argument(
        "--text-column",
        default=None,
        help="Column with input text. If omitted, uses the first match among: "
        "text, sentence, content, review, comment, tweet.",
    )
    parser.add_argument(
        "--label-column",
        default="label",
        help="Column with class labels (ints or strings).",
    )
    parser.add_argument(
        "--labels",
        default=None,
        metavar="LIST_OR_PATH",
        help=(
            "Class names in index order (comma-separated), or path to a JSON file "
            "containing [\"class_a\", ...]. If omitted: for fancyzhx/ag_news uses the "
            "standard four topic names; otherwise names are inferred from the training split."
        ),
    )
    parser.add_argument(
        "--max-train-samples", type=int, default=6000
    )
    parser.add_argument(
        "--max-eval-samples", type=int, default=1200
    )
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--vocab-size", type=int, default=8000)
    parser.add_argument("--max-seq-length", type=int, default=128)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--task-description",
        default=None,
        help="Short description for the generated model card (defaults by task).",
    )
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
class EvalMetrics:
    accuracy: float
    macro_f1: float
    weighted_f1: float
    per_class_f1: dict[str, float]
    confusion_matrix: list[list[int]]
    """Rows = true class, columns = predicted class (same order as label_names)."""


@dataclass
class TrainState:
    train_loss: float
    eval_metrics: EvalMetrics
    num_parameters: int

    @property
    def eval_accuracy(self) -> float:
        return self.eval_metrics.accuracy


def _parse_label_list(raw: str) -> list[str]:
    path = Path(raw)
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list) or not all(isinstance(x, str) for x in data):
            raise ValueError("Label JSON file must contain a JSON array of strings.")
        return data
    return [p.strip() for p in raw.split(",") if p.strip()]


def _normalize_dataset_id(ds_id: str) -> str:
    return ds_id.strip().lower().replace("\\", "/")


def _is_ag_news_dataset(ds_id: str) -> bool:
    n = _normalize_dataset_id(ds_id)
    return n == "ag_news" or n.endswith("/ag_news") or "ag_news" in n.split("/")[-1]


def infer_text_column(ds: Dataset, explicit: str | None) -> str:
    if explicit:
        if explicit not in ds.column_names:
            raise ValueError(
                f"--text-column {explicit!r} not in dataset columns {ds.column_names}"
            )
        return explicit
    candidates = (
        "text",
        "sentence",
        "content",
        "review",
        "comment",
        "tweet",
    )
    for c in candidates:
        if c in ds.column_names:
            return c
    raise ValueError(
        f"Could not infer text column from {ds.column_names}; pass --text-column."
    )


def _is_integral_label(x: object) -> bool:
    return isinstance(x, numbers.Integral) and not isinstance(x, bool)


def _sort_key_label(x: object) -> tuple:
    if _is_integral_label(x):
        return (0, float(x))
    if isinstance(x, float) and not isinstance(x, bool):
        return (0, float(x))
    return (1, str(x))


def resolve_label_names(
    dataset_id: str,
    labels_arg: str | None,
    train_ds: Dataset,
    label_col: str,
) -> list[str]:
    if labels_arg is not None:
        return _parse_label_list(labels_arg)
    if _is_ag_news_dataset(dataset_id):
        return list(AG_NEWS_LABELS)
    unique = sorted(set(train_ds[label_col]), key=_sort_key_label)
    return [str(u) for u in unique]


def build_label_maps(
    label_names: list[str],
    train_ds: Dataset,
    eval_ds: Dataset,
    label_col: str,
) -> tuple[dict[int, str], dict[object, int]]:
    """Return id2label and a map from raw label values to contiguous ids."""
    n = len(label_names)
    if n == 0:
        raise ValueError("No labels resolved.")

    raw_train = set(train_ds[label_col])
    raw_eval = set(eval_ds[label_col])
    all_raw = raw_train | raw_eval

    # Integer labels 0 .. n-1 matching name list length (e.g. AG News).
    if all(_is_integral_label(x) for x in all_raw):
        ints = sorted(int(x) for x in raw_train)
        if ints == list(range(n)):
            id2label = {i: label_names[i] for i in range(n)}
            raw_to_id = {i: i for i in range(n)}
            return id2label, raw_to_id

    # String labels: match by exact string to label_names.
    if all(isinstance(x, str) for x in all_raw):
        name_set = set(label_names)
        if set(raw_train).issubset(name_set) and raw_eval.issubset(name_set):
            id2label = {i: label_names[i] for i in range(n)}
            raw_to_id = {name: i for i, name in enumerate(label_names)}
            return id2label, raw_to_id

    # General: sorted unique raw values on training split only.
    unique = sorted(set(train_ds[label_col]), key=_sort_key_label)
    if len(unique) != n:
        raise ValueError(
            f"Expected {n} distinct training labels (from --labels or inferred), "
            f"found {len(unique)}: {unique[:20]}{'...' if len(unique) > 20 else ''}"
        )
    if label_names == [str(u) for u in unique]:
        id2label = {i: label_names[i] for i in range(n)}
        raw_to_id = {u: i for i, u in enumerate(unique)}
        return id2label, raw_to_id

    # User supplied names in same order as sorted unique raw values.
    id2label = {i: label_names[i] for i in range(n)}
    raw_to_id = {u: i for i, u in enumerate(unique)}
    return id2label, raw_to_id


def rows_to_model_inputs(
    ds: Dataset,
    text_col: str,
    label_col: str,
    raw_to_id: dict[object, int],
) -> Dataset:
    """Produce columns `text` (str) and `labels` (int)."""

    def _batch(batch: dict) -> dict:
        texts = batch[text_col]
        labs = batch[label_col]
        return {
            "text": texts,
            "labels": [raw_to_id[x] for x in labs],
        }

    return ds.map(_batch, batched=True, remove_columns=ds.column_names)


def load_splits(args: argparse.Namespace) -> tuple[Dataset, Dataset]:
    kwargs: dict = {}
    if args.dataset_config:
        kwargs["name"] = args.dataset_config
    try:
        loaded = load_dataset(args.dataset, **kwargs)
    except ValueError as e:
        err = str(e).lower()
        if "config" in err or "choice" in err:
            raise SystemExit(
                f"Dataset {args.dataset!r} requires a configuration. "
                f"Pass --dataset-config (e.g. for glue/sst2 use --dataset-config sst2)."
            ) from e
        raise
    if not isinstance(loaded, DatasetDict):
        raise SystemExit("Expected a dataset with named splits.")

    if args.train_split not in loaded:
        raise SystemExit(
            f"Train split {args.train_split!r} not found. Available: {list(loaded.keys())}"
        )
    eval_name = args.eval_split
    if eval_name not in loaded:
        alts = [s for s in ("validation", "valid", "dev", "test") if s in loaded]
        hint = f" Try one of: {alts}" if alts else ""
        raise SystemExit(
            f"Eval split {eval_name!r} not found. Available: {list(loaded.keys())}.{hint}"
        )

    train_ds = loaded[args.train_split]
    eval_ds = loaded[eval_name]
    train_ds = train_ds.shuffle(seed=args.seed).select(
        range(min(args.max_train_samples, len(train_ds)))
    )
    eval_ds = eval_ds.shuffle(seed=args.seed).select(
        range(min(args.max_eval_samples, len(eval_ds)))
    )
    return train_ds, eval_ds


def build_tokenizer(texts: list[str], vocab_size: int, output_dir: Path) -> BertTokenizerFast:
    tokenizer_model = Tokenizer(WordPiece(unk_token="<redacted_UNK>"))
    tokenizer_model.normalizer = Sequence([NFD(), Lowercase(), StripAccents()])
    tokenizer_model.pre_tokenizer = Whitespace()
    trainer = WordPieceTrainer(
        vocab_size=vocab_size,
        special_tokens=["<redacted_PAD>", "<redacted_UNK>", "[CLS]", "[SEP]", "[MASK]"],
    )
    tokenizer_model.train_from_iterator(texts, trainer=trainer)
    tokenizer_path = output_dir / "tokenizer.json"
    tokenizer_model.save(str(tokenizer_path))

    tokenizer = BertTokenizerFast(
        tokenizer_file=str(tokenizer_path),
        unk_token="<redacted_UNK>",
        sep_token="[SEP]",
        pad_token="<redacted_PAD>",
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
    ns = args.hf_namespace.strip()
    gh = args.github_repo_url.strip()
    space_repo = f"{display_name}Space"
    space_hub_url = f"https://huggingface.co/spaces/{ns}/{space_repo}"
    return f"""## Links

- **Source code (train & export):** [{gh}]({gh})
- **Live demo (Space):** [{space_repo}]({space_hub_url}) (canonical Hub URL; avoids unreliable `*.hf.space` links)
"""


def copy_model_card_image(output_dir: Path) -> bool:
    src = _REPO_ROOT / MODEL_CARD_IMAGE
    if not src.is_file():
        print(f"Note: optional model card image not found at {src}, skipping.")
        return False
    dst = output_dir / MODEL_CARD_IMAGE
    shutil.copy2(src, dst)
    print(f"Copied model card image to {dst}")
    return True


def write_model_card(
    path: Path,
    state: TrainState,
    args: argparse.Namespace,
    label_names: list[str],
) -> None:
    display_name = Path(args.output_dir).resolve().name
    out = Path(args.output_dir).resolve()
    params_m = state.num_parameters / 1_000_000.0
    banner = _model_card_banner_image_markdown(out, display_name)
    links_block = _links_markdown(args, display_name)
    n_labels = len(label_names)
    label_preview = ", ".join(label_names[:12])
    if len(label_names) > 12:
        label_preview += ", …"

    if args.task_description:
        task_blurb = args.task_description.strip()
    elif _is_ag_news_dataset(args.dataset):
        task_blurb = (
            "news topic classification, trained on the AG News dataset. "
            "It targets fast CPU/GPU inference and use as a baseline."
        )
    else:
        task_blurb = (
            f"single-label text classification with {n_labels} classes, trained on "
            f"`{args.dataset}`. It targets fast CPU/GPU inference and use as a baseline."
        )

    readme = f"""---
license: apache-2.0
library_name: transformers
pipeline_tag: text-classification
datasets:
  - {args.dataset}
language:
  - en
tags:
  - tiny
  - bert
  - text-classification
---

{banner}# {display_name}

**{display_name}** is a compact **encoder** model for **{task_blurb}**

{links_block}

---

## Model summary

| Field | Value |
|:--|:--|
| **Task** | Text classification (single-label, {n_labels} classes) |
| **Labels** | {label_preview} |
| **Dataset** | `{args.dataset}` |
| **Architecture** | Tiny BERT-style encoder (`BertForSequenceClassification`) |
| **Parameters** | {state.num_parameters:,} (~{params_m:.2f}M) |
| **Max sequence length** | {args.max_seq_length} tokens (training & inference) |
| **Framework** | [Transformers](https://github.com/huggingface/transformers) · Safetensors |

---

## Model overview

Trained with a WordPiece tokenizer fit on the training split and a shallow BERT stack. Replace the dataset and labels via `scripts/train_tinymodel1_classifier.py` for your own taxonomy.

### **Core capabilities**

- **Text routing** — assign one class per input for search, feeds, or triage.
- **Low latency** — small parameter count suits edge and serverless setups.
- **Fine-tuning base** — swap labels or data for your domain while keeping the same architecture.

---

## Training

| Setting | Value |
|:--|:--|
| **Train samples (cap)** | {args.max_train_samples} |
| **Eval samples (cap)** | {args.max_eval_samples} |
| **Epochs** | {args.epochs} |
| **Batch size** | {args.batch_size} |
| **Learning rate** | {args.learning_rate} |
| **Optimizer** | AdamW |

---

## Evaluation

| Metric | Value |
|:--|:--|
| **Accuracy** | {state.eval_metrics.accuracy:.4f} |
| **Macro F1** | {state.eval_metrics.macro_f1:.4f} |
| **Weighted F1** | {state.eval_metrics.weighted_f1:.4f} |
| **Final train loss** | {state.train_loss:.4f} |

Per-class F1 and the confusion matrix are saved in `eval_report.json` in this model directory.

Metrics are computed on the held-out eval subset (see `eval_report.json` → `reproducibility`); treat them as a **sanity-check baseline**, not a production SLA.

---

## Getting started

### Inference with `transformers`

```python
from transformers import pipeline

clf = pipeline(
    "text-classification",
    model="{display_name}",
    tokenizer="{display_name}",
    top_k=None,
)
text = "Your input text here."
print(clf(text))
```

Use `top_k=None` (or your Transformers version’s equivalent) for scores for **all** labels. Replace `"{display_name}"` with your Hub model id when loading from the Hub.

---

## Training data

- **Dataset:** `{args.dataset}` (text column mapped for training; see `artifact.json`).
- **Preprocessing:** tokenizer trained on training texts; sequences truncated to {args.max_seq_length} tokens.

---

## Intended use

- Prototyping **routing**, **tagging**, and **dashboard** features over short text.
- Teaching and benchmarking small-classification setups.
- Starting point for **domain adaptation** with your own labels.

---

## Limitations

- **Accuracy** is modest by design; validate on your data before high-stakes use.
- **Not a general-purpose language model** — classification head only; for generation use an LM.
- **Tokenizer and labels** are tied to this training run; mismatched inputs may degrade.

---

## License

This model is released under the **Apache 2.0** license (see repository `LICENSE` where applicable).
"""
    path.write_text(readme, encoding="utf-8")


def write_manifest(
    path: Path,
    state: TrainState,
    args: argparse.Namespace,
    label_names: list[str],
    text_col: str,
) -> None:
    display_name = Path(args.output_dir).resolve().name
    m = state.eval_metrics
    data = {
        "name": display_name,
        "version": "0.3.0",
        "task": "text-classification",
        "dataset": args.dataset,
        "dataset_config": args.dataset_config,
        "train_split": args.train_split,
        "eval_split": args.eval_split,
        "text_column": text_col,
        "label_column": args.label_column,
        "base_model": "tinymodel1-bert-scratch",
        "labels": label_names,
        "eval_accuracy": round(m.accuracy, 4),
        "eval_macro_f1": round(m.macro_f1, 4),
        "eval_weighted_f1": round(m.weighted_f1, 4),
        "eval_per_class_f1": {k: round(v, 4) for k, v in m.per_class_f1.items()},
        "train_loss": round(state.train_loss, 4),
        "num_parameters": state.num_parameters,
        "max_train_samples": args.max_train_samples,
        "max_eval_samples": args.max_eval_samples,
        "max_seq_length": args.max_seq_length,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "learning_rate": args.learning_rate,
        "seed": args.seed,
    }
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def write_eval_report(
    path: Path,
    state: TrainState,
    args: argparse.Namespace,
    label_names: list[str],
    text_col: str,
) -> None:
    m = state.eval_metrics
    payload = {
        "reproducibility": {
            "seed": args.seed,
            "dataset": args.dataset,
            "dataset_config": args.dataset_config,
            "train_split": args.train_split,
            "eval_split": args.eval_split,
            "text_column": text_col,
            "label_column": args.label_column,
            "max_train_samples": args.max_train_samples,
            "max_eval_samples": args.max_eval_samples,
            "note": (
                "Train and eval rows are the first N after shuffle(seed) of each split; "
                "see texts/eval-reproducibility.md."
            ),
        },
        "metrics": {
            "accuracy": round(m.accuracy, 6),
            "macro_f1": round(m.macro_f1, 6),
            "weighted_f1": round(m.weighted_f1, 6),
            "per_class_f1": {k: round(v, 6) for k, v in m.per_class_f1.items()},
            "confusion_matrix": m.confusion_matrix,
            "confusion_matrix_axis": "rows=true class, columns=predicted class",
            "label_order": list(label_names),
        },
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _metrics_from_confusion(
    cm: np.ndarray,
    label_names: list[str],
) -> EvalMetrics:
    """cm[i,j] = count with true class i, predicted j."""
    n_classes = cm.shape[0]
    per_class_f1: dict[str, float] = {}
    f1s: list[float] = []
    supports: list[int] = []
    for k in range(n_classes):
        tp = float(cm[k, k])
        fp = float(cm[:, k].sum() - cm[k, k])
        fn = float(cm[k, :].sum() - cm[k, k])
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        if prec + rec == 0:
            f1 = 0.0
        else:
            f1 = 2.0 * prec * rec / (prec + rec)
        per_class_f1[label_names[k]] = f1
        f1s.append(f1)
        supports.append(int(cm[k, :].sum()))
    total = float(cm.sum())
    accuracy = float(np.trace(cm) / total) if total > 0 else 0.0
    macro_f1 = float(np.mean(f1s)) if f1s else 0.0
    weighted_f1 = (
        float(sum(f * s for f, s in zip(f1s, supports)) / total) if total > 0 else 0.0
    )
    return EvalMetrics(
        accuracy=accuracy,
        macro_f1=macro_f1,
        weighted_f1=weighted_f1,
        per_class_f1=per_class_f1,
        confusion_matrix=cm.astype(int).tolist(),
    )


def evaluate(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
    num_labels: int,
    label_names: list[str],
) -> EvalMetrics:
    model.eval()
    all_labels: list[int] = []
    all_preds: list[int] = []
    with torch.no_grad():
        for batch in loader:
            labels = batch.pop("labels").to(device)
            batch = {k: v.to(device) for k, v in batch.items()}
            logits = model(**batch).logits
            preds = torch.argmax(logits, dim=-1)
            all_labels.extend(labels.cpu().numpy().tolist())
            all_preds.extend(preds.cpu().numpy().tolist())

    cm = np.zeros((num_labels, num_labels), dtype=np.int64)
    for t, p in zip(all_labels, all_preds):
        cm[int(t), int(p)] += 1
    return _metrics_from_confusion(cm, label_names)


def resolve_device() -> torch.device:
    if not torch.cuda.is_available():
        return torch.device("cpu")
    try:
        major, minor = torch.cuda.get_device_capability(0)
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

    train_raw, eval_raw = load_splits(args)

    text_col = infer_text_column(train_raw, args.text_column)
    if args.label_column not in train_raw.column_names:
        raise SystemExit(
            f"--label-column {args.label_column!r} not in columns {train_raw.column_names}"
        )

    label_names = resolve_label_names(args.dataset, args.labels, train_raw, args.label_column)
    id2label_map, raw_to_id = build_label_maps(
        label_names, train_raw, eval_raw, args.label_column
    )
    num_labels = len(id2label_map)

    train_ds = rows_to_model_inputs(train_raw, text_col, args.label_column, raw_to_id)
    eval_ds = rows_to_model_inputs(eval_raw, text_col, args.label_column, raw_to_id)

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
        num_labels=num_labels,
        id2label={i: id2label_map[i] for i in range(num_labels)},
        label2id={id2label_map[i]: i for i in range(num_labels)},
    )
    model = BertForSequenceClassification(config)

    max_len = args.max_seq_length

    def tokenize(batch: dict[str, list[str]]) -> dict[str, list[int]]:
        return tokenizer(batch["text"], truncation=True, max_length=max_len)

    train_ds = train_ds.map(tokenize, batched=True)
    eval_ds = eval_ds.map(tokenize, batched=True)
    train_ds.set_format(
        type="torch", columns=["input_ids", "attention_mask", "labels"]
    )
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

    eval_metrics = evaluate(
        model, eval_loader, device, num_labels=num_labels, label_names=label_names
    )
    print(f"eval_accuracy={eval_metrics.accuracy:.4f}")
    print(f"eval_macro_f1={eval_metrics.macro_f1:.4f}")
    print(f"eval_weighted_f1={eval_metrics.weighted_f1:.4f}")
    for name, f1 in eval_metrics.per_class_f1.items():
        print(f"  f1[{name}]={f1:.4f}")

    num_parameters = int(sum(p.numel() for p in model.parameters()))

    model.save_pretrained(output_dir, safe_serialization=True)
    tokenizer.save_pretrained(output_dir)

    copy_model_card_image(output_dir)

    state = TrainState(
        train_loss=last_loss, eval_metrics=eval_metrics, num_parameters=num_parameters
    )
    write_model_card(output_dir / "README.md", state, args, label_names)
    write_manifest(output_dir / "artifact.json", state, args, label_names, text_col)
    write_eval_report(output_dir / "eval_report.json", state, args, label_names, text_col)
    print(f"Saved classifier to: {output_dir}")
    print(f"Wrote eval_report.json with confusion matrix and per-class F1.")


if __name__ == "__main__":
    main()
