#!/usr/bin/env python3
"""Phase 1 runner: reproducible presets + baseline comparison matrix."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
from pathlib import Path


PRESETS: dict[str, dict[str, int]] = {
    "smoke": {
        "max_train_samples": 120,
        "max_eval_samples": 80,
        "epochs": 1,
        "batch_size": 8,
    },
    "dev": {
        "max_train_samples": 1000,
        "max_eval_samples": 300,
        "epochs": 2,
        "batch_size": 16,
    },
    "full": {
        "max_train_samples": 6000,
        "max_eval_samples": 1200,
        "epochs": 3,
        "batch_size": 16,
    },
}

DATASETS: dict[str, dict[str, str]] = {
    "ag_news": {
        "dataset": "fancyzhx/ag_news",
        "eval_split": "test",
        "labels": "World,Sports,Business,Sci/Tech",
    },
    "emotion": {
        "dataset": "emotion",
        "eval_split": "validation",
        "labels": "sadness,joy,love,anger,fear,surprise",
    },
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--preset", choices=sorted(PRESETS), default="smoke")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument(
        "--datasets",
        default="ag_news,emotion",
        help="Comma-separated subset of: ag_news,emotion.",
    )
    p.add_argument(
        "--models",
        default="scratch,pretrained",
        help="Comma-separated subset of: scratch,pretrained.",
    )
    p.add_argument(
        "--base-model",
        default="distilbert-base-uncased",
        help="Transformers id used when pretrained mode is enabled.",
    )
    p.add_argument(
        "--output-root",
        default="artifacts/phase1",
        help="Where run artifacts and comparison tables are written.",
    )
    p.add_argument(
        "--retries",
        type=int,
        default=1,
        help="Number of retries per run when a subprocess exits non-zero.",
    )
    p.add_argument(
        "--reuse-existing",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="If true, skip launching a run when required artifacts already exist.",
    )
    return p.parse_args()


def _split_csv(raw: str) -> list[str]:
    return [x.strip() for x in raw.split(",") if x.strip()]


def _run(cmd: list[str], retries: int) -> None:
    print("$", " ".join(cmd))
    last_err: subprocess.CalledProcessError | None = None
    for attempt in range(retries + 1):
        try:
            subprocess.run(cmd, check=True)
            return
        except subprocess.CalledProcessError as exc:
            last_err = exc
            if attempt >= retries:
                break
            print(
                f"Command failed with code {exc.returncode}; retrying "
                f"({attempt + 1}/{retries})..."
            )
            time.sleep(2)
    assert last_err is not None
    raise last_err


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_row(dataset_key: str, model_key: str, run_dir: Path) -> dict:
    eval_report = _read_json(run_dir / "eval_report.json")
    metrics = eval_report["metrics"]
    reproducibility = eval_report["reproducibility"]
    row: dict[str, object] = {
        "dataset": dataset_key,
        "model": model_key,
        "seed": reproducibility["seed"],
        "max_train_samples": reproducibility["max_train_samples"],
        "max_eval_samples": reproducibility["max_eval_samples"],
        "accuracy": metrics["accuracy"],
        "macro_f1": metrics["macro_f1"],
    }
    for label, f1 in metrics["per_class_f1"].items():
        row[f"f1_{label}"] = f1
    return row


def _write_table_json(path: Path, rows: list[dict]) -> None:
    path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")


def _write_table_csv(path: Path, rows: list[dict]) -> None:
    keys: list[str] = []
    for row in rows:
        for k in row:
            if k not in keys:
                keys.append(k)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def _write_table_md(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("# Phase 1 comparison\n\nNo rows.\n", encoding="utf-8")
        return
    base_keys = [
        "dataset",
        "model",
        "seed",
        "max_train_samples",
        "max_eval_samples",
        "accuracy",
        "macro_f1",
    ]
    extra_keys = sorted(
        {
            k
            for row in rows
            for k in row.keys()
            if k not in set(base_keys)
        }
    )
    keys = base_keys + extra_keys
    lines = [
        "# Phase 1 comparison matrix",
        "",
        "| " + " | ".join(keys) + " |",
        "| " + " | ".join(["---"] * len(keys)) + " |",
    ]
    for row in rows:
        vals = [str(row.get(k, "")) for k in keys]
        lines.append("| " + " | ".join(vals) + " |")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    preset_cfg = PRESETS[args.preset]
    datasets = _split_csv(args.datasets)
    models = _split_csv(args.models)

    allowed_datasets = set(DATASETS)
    allowed_models = {"scratch", "pretrained"}

    unknown_ds = [d for d in datasets if d not in allowed_datasets]
    if unknown_ds:
        raise SystemExit(f"Unknown datasets: {unknown_ds}. Allowed: {sorted(allowed_datasets)}")
    unknown_models = [m for m in models if m not in allowed_models]
    if unknown_models:
        raise SystemExit(f"Unknown models: {unknown_models}. Allowed: {sorted(allowed_models)}")

    output_root = Path(args.output_root).resolve()
    run_root = output_root / "runs" / args.preset
    report_root = output_root / "reports"
    run_root.mkdir(parents=True, exist_ok=True)
    report_root.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    py = sys.executable

    for dataset_key in datasets:
        ds = DATASETS[dataset_key]
        for model_key in models:
            run_dir = run_root / dataset_key / model_key
            run_dir.mkdir(parents=True, exist_ok=True)
            common = [
                "--output-dir",
                str(run_dir),
                "--dataset",
                ds["dataset"],
                "--eval-split",
                ds["eval_split"],
                "--labels",
                ds["labels"],
                "--max-train-samples",
                str(preset_cfg["max_train_samples"]),
                "--max-eval-samples",
                str(preset_cfg["max_eval_samples"]),
                "--epochs",
                str(preset_cfg["epochs"]),
                "--batch-size",
                str(preset_cfg["batch_size"]),
                "--seed",
                str(args.seed),
            ]
            required = ["eval_report.json", "artifact.json", "config.json"]
            missing_before = [name for name in required if not (run_dir / name).is_file()]
            if missing_before or not args.reuse_existing:
                if model_key == "scratch":
                    cmd = [py, "scripts/train_tinymodel1_classifier.py"] + common
                else:
                    cmd = [py, "scripts/finetune_pretrained_classifier.py"] + common + [
                        "--base-model",
                        args.base_model,
                    ]
                try:
                    _run(cmd, retries=max(0, args.retries))
                except subprocess.CalledProcessError:
                    # On some Windows CPU stacks, pretrained fine-tune may intermittently
                    # crash at native level. If valid artifacts already exist, reuse them.
                    missing_after_failure = [
                        name for name in required if not (run_dir / name).is_file()
                    ]
                    if missing_after_failure:
                        raise
                    print(
                        "Command failed but existing artifacts are valid; reusing prior "
                        f"outputs in {run_dir}."
                    )
            else:
                print(f"Reusing existing artifacts in: {run_dir}")

            missing = [name for name in required if not (run_dir / name).is_file()]
            if missing:
                raise SystemExit(f"Run failed verification for {run_dir}: missing {missing}")
            rows.append(_extract_row(dataset_key, model_key, run_dir))

    stamp = f"phase1_{args.preset}_seed{args.seed}"
    _write_table_json(report_root / f"{stamp}.json", rows)
    _write_table_csv(report_root / f"{stamp}.csv", rows)
    _write_table_md(report_root / f"{stamp}.md", rows)
    print(f"Wrote comparison reports under: {report_root}")


if __name__ == "__main__":
    main()
