#!/usr/bin/env python3
"""Train TinyModel1 on GLUE SST-2 (binary sentiment, domain-relevant third reference task).

Delegates to `train_tinymodel1_classifier.py`. Dataset: `glue` + config `sst2`; eval split defaults to `validation`.

For other Hub datasets, call `train_tinymodel1_classifier.py` directly.
"""

from __future__ import annotations

import sys
from pathlib import Path

_scripts = Path(__file__).resolve().parent
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))

_SST2_DEFAULTS = [
    "--dataset",
    "glue",
    "--dataset-config",
    "sst2",
    "--train-split",
    "train",
    "--eval-split",
    "validation",
    "--labels",
    "negative,positive",
]

if __name__ == "__main__":
    sys.argv = [sys.argv[0]] + _SST2_DEFAULTS + sys.argv[1:]
    from train_tinymodel1_classifier import main  # noqa: E402

    main()
