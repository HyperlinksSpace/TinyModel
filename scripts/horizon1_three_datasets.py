#!/usr/bin/env python3
"""Train three reference tasks (AG News, Emotion, SST-2) with shared caps for Horizon 1 breadth (short-term plan B)."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--output-root",
        type=str,
        default="artifacts/horizon1/three-tasks",
        help="Per-dataset model directories are created under this path.",
    )
    p.add_argument("--max-train-samples", type=int, default=300)
    p.add_argument("--max-eval-samples", type=int, default=150)
    p.add_argument("--epochs", type=int, default=1)
    p.add_argument("--batch-size", type=int, default=8)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument(
        "--max-misclassified-examples",
        type=int,
        default=30,
        help="Phase 2 misclassified sample size per run.",
    )
    p.add_argument(
        "--summary-md",
        type=str,
        default="texts/horizon1-three-tasks-summary.md",
        help="Write human-readable comparison (relative to repo root).",
    )
    p.add_argument(
        "--summary-json",
        type=str,
        default="artifacts/horizon1/three-tasks-summary.json",
    )
    p.add_argument(
        "--offline-datasets",
        action="store_true",
        help="Set HF_DATASETS_OFFLINE=1 so Hugging Face uses only local cache (avoids Hub timeouts).",
    )
    return p.parse_args()


def run_one(
    script: str,
    out: Path,
    a: argparse.Namespace,
) -> None:
    cmd = [
        sys.executable,
        str(_REPO / "scripts" / script),
        "--output-dir",
        str(out),
        "--max-train-samples",
        str(a.max_train_samples),
        "--max-eval-samples",
        str(a.max_eval_samples),
        "--epochs",
        str(a.epochs),
        "--batch-size",
        str(a.batch_size),
        "--seed",
        str(a.seed),
        "--max-misclassified-examples",
        str(a.max_misclassified_examples),
    ]
    print("+", " ".join(cmd), flush=True)
    env = {**os.environ}
    if a.offline_datasets:
        env["HF_DATASETS_OFFLINE"] = "1"
    try:
        subprocess.run(cmd, cwd=str(_REPO), check=True, env=env)
    except subprocess.CalledProcessError:
        if not a.offline_datasets:
            print(
                "horizon1_three_datasets: training step failed. If you see ReadTimeout/SSL/proxy "
                "errors to huggingface.co, use a stable network, fix HTTP(S)_PROXY, or re-run with "
                "--offline-datasets after datasets are in the local Hub cache (see "
                "texts/horizon1-short-term-handbook.md).",
                file=sys.stderr,
            )
        raise


def main() -> None:
    a = parse_args()
    root = _REPO / a.output_root
    root.mkdir(parents=True, exist_ok=True)

    tasks: list[tuple[str, str]] = [
        ("ag_news", "train_tinymodel1_agnews.py"),
        ("emotion", "train_tinymodel1_emotion.py"),
        ("sst2", "train_tinymodel1_sst2.py"),
    ]

    for sub, script in tasks:
        run_one(script, root / sub, a)

    rows: list[dict[str, object]] = []
    for sub, _ in tasks:
        er = root / sub / "eval_report.json"
        if not er.is_file():
            print(f"Missing {er}", file=sys.stderr)
            raise SystemExit(1)
        d = json.loads(er.read_text(encoding="utf-8"))
        m = d.get("metrics", {})
        rep = d.get("reproducibility", {})
        rows.append(
            {
                "task": sub,
                "dataset": rep.get("dataset"),
                "accuracy": m.get("accuracy"),
                "macro_f1": m.get("macro_f1"),
                "output_dir": str((root / sub).resolve()),
            }
        )

    jpath = _REPO / a.summary_json
    jpath.parent.mkdir(parents=True, exist_ok=True)
    jpath.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {jpath}")

    md = _REPO / a.summary_md
    lines = [
        "# Horizon 1 (short term): three-dataset run summary",
        "",
        f"Trained with shared caps: train={a.max_train_samples}, eval={a.max_eval_samples}, "
        f"epochs={a.epochs}, batch={a.batch_size}, seed={a.seed}.",
        "",
        "| Task | dataset (Hub) | accuracy | macro_f1 |",
        "| ---- | -------------- | -------- | -------- |",
    ]
    for r in rows:
        acc = r.get("accuracy")
        mf = r.get("macro_f1")
        lines.append(
            f"| {r['task']} | {r.get('dataset', '')} | {acc} | {mf} |"
        )
    lines += [
        "",
        "Per-task directories (each has `eval_report.json`, `misclassified_sample.jsonl`, model files):",
        "",
    ]
    for r in rows:
        outp = Path(str(r["output_dir"]))
        try:
            out_rel = outp.resolve().relative_to(_REPO.resolve())
            out_show = out_rel.as_posix()
        except ValueError:
            out_show = outp.as_posix()
        lines.append(f"- **{r['task']}:** `{out_show}`")
    first = rows[0]
    outp0 = Path(str(first["output_dir"])).resolve()
    try:
        ex_show = outp0.relative_to(_REPO.resolve()).as_posix()
    except ValueError:
        ex_show = outp0.as_posix()
    lines += [
        "",
        "## Phase 2 `routing` quick check",
        "",
        "Each task directory contains **`eval_report.json`** with top-level **`routing`** when using current training scripts. Example for the **first table row** (`ag_news`):",
        "",
        f"`python scripts/routing_policy.py --from-checkpoint {ex_show}`",
        "",
        "See **README** (Phase 2 and Horizon 1 route-to-RAG).",
        "",
        "See [`further-development-universe-brain.md`](further-development-universe-brain.md) short-term block **B**.",
        "",
    ]
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {md}")
    print(
        "Tip: Phase 2 `routing` for first task row (also in the summary .md footer):\n"
        f"  python scripts/routing_policy.py --from-checkpoint {ex_show}",
        flush=True,
    )


if __name__ == "__main__":
    main()
