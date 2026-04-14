#!/usr/bin/env python3
"""Regenerate README.md (Hub model card) from the template in train_tinymodel1_agnews.py.

Uses metrics and hyperparameters in artifact.json (next to weights). Safe to run after
snapshot_download of an existing Hub model to refresh the card without retraining.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from train_tinymodel1_agnews import TrainState, write_model_card  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Regenerate model card README.md without retraining."
    )
    parser.add_argument(
        "--artifact-dir",
        required=True,
        help="Folder with model files, tokenizer, and artifact.json.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(args.artifact_dir).resolve()
    artifact_path = root / "artifact.json"
    if not artifact_path.is_file():
        raise FileNotFoundError(
            f"Missing {artifact_path}. Train or download a model snapshot first."
        )

    data = json.loads(artifact_path.read_text(encoding="utf-8"))

    state = TrainState(
        train_loss=float(data.get("train_loss", 0.0)),
        eval_accuracy=float(data.get("eval_accuracy", 0.0)),
    )

    # Defaults match scripts/train_tinymodel1_agnews.py (older artifact.json may omit keys).
    ns = SimpleNamespace(
        output_dir=str(root),
        max_train_samples=int(data.get("max_train_samples", 6000)),
        max_eval_samples=int(data.get("max_eval_samples", 1200)),
        epochs=int(data.get("epochs", 3)),
        batch_size=int(data.get("batch_size", 16)),
        learning_rate=float(data.get("learning_rate", 1e-4)),
    )

    out = root / "README.md"
    write_model_card(out, state, ns)
    print(f"Wrote model card: {out}")


if __name__ == "__main__":
    main()
