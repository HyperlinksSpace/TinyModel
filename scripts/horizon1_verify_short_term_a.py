#!/usr/bin/env python3
"""Local verification for short-term horizon **A** (tactical stack shippable end-to-end).

Runs the same commands as CI locally: Phase 1 smoke matrix, then a fresh tiny train with
full Phase 2 eval, then Phase 3 ONNX export + parity + quick benchmark.

Exit 0 means your environment matches the expectations in `further-development-plan.md`
and `further-development-universe-brain.md` (short-term A)."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from eval_report_routing import print_routing_policy_from_checkpoint_tip

_REPO = Path(__file__).resolve().parent.parent


def run(cmd: list[str]) -> None:
    import os

    print("+", " ".join(cmd), flush=True)
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    subprocess.run(cmd, cwd=str(_REPO), check=True, env=env)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--skip-phase3",
        action="store_true",
        help="Only Phase 1 + fresh train (no ONNX; needs optional Phase 3 deps).",
    )
    args = p.parse_args()

    run(
        [
            sys.executable,
            str(_REPO / "scripts" / "phase1_compare.py"),
            "--preset",
            "smoke",
            "--models",
            "scratch",
            "--datasets",
            "ag_news,emotion",
            "--seed",
            "42",
        ]
    )
    phase1_md = _REPO / "artifacts/phase1/reports/phase1_smoke_seed42.md"
    if not phase1_md.is_file():
        print(f"Missing {phase1_md}", file=sys.stderr)
        raise SystemExit(1)

    out = _REPO / ".tmp/horizon1-verify-a"
    run(
        [
            sys.executable,
            str(_REPO / "scripts" / "train_tinymodel1_classifier.py"),
            "--output-dir",
            str(out),
            "--max-train-samples",
            "64",
            "--max-eval-samples",
            "32",
            "--epochs",
            "1",
            "--batch-size",
            "8",
            "--seed",
            "42",
            "--max-misclassified-examples",
            "5",
        ]
    )
    import json

    er = json.loads((out / "eval_report.json").read_text(encoding="utf-8"))
    for k in ("dataset_quality", "error_analysis", "calibration", "routing"):
        if k not in er:
            print(f"eval_report.json missing Phase 2 key: {k}", file=sys.stderr)
            raise SystemExit(1)

    print_routing_policy_from_checkpoint_tip(
        out,
        headline="Tip: dump Phase 2 `routing` JSON from this train dir (no model load):",
        cwd=_REPO,
    )

    if args.skip_phase3:
        print("horizon1_verify_short_term_a: OK (Phase 1 + fresh train with Phase 2 fields).")
        return

    run(
        [
            sys.executable,
            str(_REPO / "scripts" / "phase3_export_onnx.py"),
            "--model",
            str(out),
        ]
    )
    run(
        [
            sys.executable,
            str(_REPO / "scripts" / "phase3_onnx_parity.py"),
            "--model",
            str(out),
        ]
    )
    run(
        [
            sys.executable,
            str(_REPO / "scripts" / "phase3_benchmark.py"),
            "--model",
            str(out),
            "--repeats",
            "8",
            "--warmup",
            "2",
        ]
    )
    print("horizon1_verify_short_term_a: OK (Phase 1 + Phase 2 train + Phase 3 export/parity/bench).")


if __name__ == "__main__":
    main()
