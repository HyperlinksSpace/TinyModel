#!/usr/bin/env python3
"""Fine-tune a pretrained encoder (DistilBERT/BERT/RoBERTa) for Hub text classification.

Uses the same dataset loading and eval metrics as `train_tinymodel1_classifier.py`, but
loads `AutoTokenizer` / `AutoModelForSequenceClassification` from `--base-model` instead
of training a tiny BERT from scratch. Compare `eval_report.json` against a scratch run
on the same `--seed` and sample caps to judge whether PEFT/LoRA on larger models is next.

Example (AG News, quick CPU smoke — downloads `distilbert-base-uncased` once):

    python scripts/finetune_pretrained_classifier.py \\
      --output-dir artifacts/finetune-smoke \\
      --base-model distilbert-base-uncased \\
      --max-train-samples 400 --max-eval-samples 200 \\
      --epochs 1 --batch-size 8 --seed 42
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

# Runtime stability knobs for Windows CPU environments.
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import torch
from torch.utils.data import DataLoader
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
)

_scripts = Path(__file__).resolve().parent
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))

from train_tinymodel1_classifier import (  # noqa: E402
    TrainState,
    evaluate,
    infer_text_column,
    load_splits,
    resolve_label_names,
    resolve_device,
    rows_to_model_inputs,
    set_seed,
    build_label_maps,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--base-model",
        default="distilbert-base-uncased",
        help="Transformers model id for weights + tokenizer (e.g. distilbert-base-uncased).",
    )
    p.add_argument("--output-dir", default="artifacts/TinyModel1-pretrained")
    p.add_argument("--dataset", default="fancyzhx/ag_news")
    p.add_argument("--dataset-config", default=None)
    p.add_argument("--train-split", default="train")
    p.add_argument("--eval-split", default="test")
    p.add_argument("--text-column", default=None)
    p.add_argument("--label-column", default="label")
    p.add_argument("--labels", default=None)
    p.add_argument("--max-train-samples", type=int, default=6000)
    p.add_argument("--max-eval-samples", type=int, default=1200)
    p.add_argument("--epochs", type=int, default=2)
    p.add_argument("--batch-size", type=int, default=16)
    p.add_argument("--learning-rate", type=float, default=5e-5)
    p.add_argument("--max-seq-length", type=int, default=128)
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def _split_args_for_loader(args: argparse.Namespace) -> SimpleNamespace:
    return SimpleNamespace(
        dataset=args.dataset,
        dataset_config=args.dataset_config,
        train_split=args.train_split,
        eval_split=args.eval_split,
        max_train_samples=args.max_train_samples,
        max_eval_samples=args.max_eval_samples,
        seed=args.seed,
    )


def _split_args_for_reports(args: argparse.Namespace) -> SimpleNamespace:
    """Namespace compatible with `write_eval_report` / manifest-style fields."""
    return SimpleNamespace(
        output_dir=args.output_dir,
        dataset=args.dataset,
        dataset_config=args.dataset_config,
        train_split=args.train_split,
        eval_split=args.eval_split,
        text_column=args.text_column,
        label_column=args.label_column,
        labels=args.labels,
        max_train_samples=args.max_train_samples,
        max_eval_samples=args.max_eval_samples,
        max_seq_length=args.max_seq_length,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        seed=args.seed,
    )


def main() -> None:
    args = parse_args()
    set_seed(args.seed)
    # Windows CPU runs can hit low-level segfaults in some Torch+Transformer combos.
    torch.backends.mkldnn.enabled = False
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    load_ns = _split_args_for_loader(args)
    train_raw, eval_raw = load_splits(load_ns)

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

    tokenizer = AutoTokenizer.from_pretrained(args.base_model)
    max_len = args.max_seq_length

    def tokenize(batch: dict) -> dict:
        enc = tokenizer(
            batch["text"],
            truncation=True,
            max_length=max_len,
            padding=False,
        )
        return enc

    train_tok = train_ds.map(tokenize, batched=True)
    eval_tok = eval_ds.map(tokenize, batched=True)
    train_tok = train_tok.remove_columns(["text"])
    eval_tok = eval_tok.remove_columns(["text"])

    id2label = {i: id2label_map[i] for i in range(num_labels)}
    label2id = {id2label_map[i]: i for i in range(num_labels)}
    model = AutoModelForSequenceClassification.from_pretrained(
        args.base_model,
        num_labels=num_labels,
        id2label=id2label,
        label2id=label2id,
    )

    data_collator = DataCollatorWithPadding(tokenizer=tokenizer)
    train_tok.set_format(
        type="torch",
        columns=["input_ids", "attention_mask", "labels"],
    )
    train_loader = DataLoader(
        train_tok,
        batch_size=args.batch_size,
        shuffle=True,
        collate_fn=data_collator,
    )

    device = resolve_device()
    model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate)
    model.train()
    train_loss = 0.0
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

            running_loss += float(loss.item())
            steps += 1
        train_loss = running_loss / max(1, steps)
        print(f"epoch={epoch + 1} train_loss={train_loss:.4f}")

    model.save_pretrained(output_dir, safe_serialization=True)
    tokenizer.save_pretrained(output_dir)

    eval_tok.set_format(
        type="torch",
        columns=["input_ids", "attention_mask", "labels"],
    )
    collator = DataCollatorWithPadding(tokenizer=tokenizer)
    eval_loader = DataLoader(
        eval_tok,
        batch_size=args.batch_size,
        shuffle=False,
        collate_fn=collator,
    )
    eval_metrics = evaluate(model, eval_loader, device, num_labels, label_names)

    num_parameters = int(sum(p.numel() for p in model.parameters()))
    state = TrainState(
        train_loss=train_loss,
        eval_metrics=eval_metrics,
        num_parameters=num_parameters,
    )

    report_ns = _split_args_for_reports(args)
    from train_tinymodel1_classifier import write_eval_report  # noqa: E402

    write_eval_report(output_dir / "eval_report.json", state, report_ns, label_names, text_col)

    payload = json.loads((output_dir / "eval_report.json").read_text(encoding="utf-8"))
    payload["reproducibility"]["base_model"] = args.base_model
    payload["reproducibility"]["finetune_script"] = "finetune_pretrained_classifier.py"
    (output_dir / "eval_report.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )

    manifest = {
        "name": output_dir.resolve().name,
        "task": "text-classification",
        "dataset": args.dataset,
        "dataset_config": args.dataset_config,
        "train_split": args.train_split,
        "eval_split": args.eval_split,
        "text_column": text_col,
        "label_column": args.label_column,
        "base_model": args.base_model,
        "labels": label_names,
        "eval_accuracy": round(eval_metrics.accuracy, 4),
        "eval_macro_f1": round(eval_metrics.macro_f1, 4),
        "eval_weighted_f1": round(eval_metrics.weighted_f1, 4),
        "train_loss": round(train_loss, 4),
        "num_parameters": num_parameters,
        "max_train_samples": args.max_train_samples,
        "max_eval_samples": args.max_eval_samples,
        "seed": args.seed,
    }
    (output_dir / "artifact.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"eval_accuracy={eval_metrics.accuracy:.4f} eval_macro_f1={eval_metrics.macro_f1:.4f}")
    print(f"Saved to {output_dir}")


if __name__ == "__main__":
    main()
