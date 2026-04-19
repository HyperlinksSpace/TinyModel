#!/usr/bin/env python3
"""Train TinyModel1 on the Hugging Face `emotion` dataset (second reference task).

This is a thin preset over `train_tinymodel1_classifier.py` — same stack, different Hub
dataset and label names. Defaults are applied first; arguments you pass afterward
override (e.g. `--output-dir`, sample caps, `--seed`).

Dataset: `emotion` (6-class English tweets). Splits: `train`, `validation`, `test`.
Eval defaults to `validation` so you can keep `test` fully held out if desired.

For any other Hub dataset, call `train_tinymodel1_classifier.py` directly.
"""

from __future__ import annotations

import sys
from pathlib import Path

_scripts = Path(__file__).resolve().parent
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))

# Preset must come before user args so later flags override (argparse: last wins).
_EMOTION_DEFAULTS = [
    "--dataset",
    "emotion",
    "--eval-split",
    "validation",
    "--labels",
    "sadness,joy,love,anger,fear,surprise",
]

if __name__ == "__main__":
    sys.argv = [sys.argv[0]] + _EMOTION_DEFAULTS + sys.argv[1:]
    from train_tinymodel1_classifier import main  # noqa: E402

    main()
