"""Top-level --help for ``scripts/horizon1_three_datasets.py`` (no training subprocess)."""

from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_REPO = Path(__file__).resolve().parent.parent
_SCRIPTS = _REPO / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import horizon1_three_datasets as h1t  # noqa: E402


class TestHorizon1ThreeDatasetsHelp(unittest.TestCase):
    def test_help_lists_offline_and_scripts(self) -> None:
        out = io.StringIO()
        err = io.StringIO()
        with patch.object(sys, "argv", ["horizon1_three_datasets.py", "-h"]):
            with patch.object(sys, "stdout", out), patch.object(sys, "stderr", err):
                with self.assertRaises(SystemExit) as ctx:
                    h1t.parse_args()
        self.assertEqual(ctx.exception.code, 0)
        combined = out.getvalue() + err.getvalue()
        self.assertIn("--offline-datasets", combined)
        self.assertIn("train_tinymodel1_agnews", combined)


if __name__ == "__main__":
    unittest.main()
