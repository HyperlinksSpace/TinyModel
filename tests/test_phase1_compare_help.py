"""Top-level --help for ``scripts/phase1_compare.py`` (no training subprocess)."""

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

import phase1_compare as p1  # noqa: E402


class TestPhase1CompareHelp(unittest.TestCase):
    def test_help_lists_presets_and_ci_example(self) -> None:
        out = io.StringIO()
        err = io.StringIO()
        with patch.object(sys, "argv", ["phase1_compare.py", "-h"]):
            with patch.object(sys, "stdout", out), patch.object(sys, "stderr", err):
                with self.assertRaises(SystemExit) as ctx:
                    p1.parse_args()
        self.assertEqual(ctx.exception.code, 0)
        combined = out.getvalue() + err.getvalue()
        self.assertIn("--preset", combined)
        self.assertIn("--models scratch", combined)
        self.assertIn("ag_news,emotion", combined)


if __name__ == "__main__":
    unittest.main()
