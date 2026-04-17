#!/usr/bin/env python3
"""Train TinyModel1 on AG News (compatibility wrapper).

Delegates to `train_tinymodel1_classifier.py` with defaults matching the original
AG News recipe (fancyzhx/ag_news). For other datasets, use:

    python scripts/train_tinymodel1_classifier.py --dataset <hub_id> ...
"""

from __future__ import annotations

import sys
from pathlib import Path

_scripts = Path(__file__).resolve().parent
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))

from train_tinymodel1_classifier import main  # noqa: E402

if __name__ == "__main__":
    main()
