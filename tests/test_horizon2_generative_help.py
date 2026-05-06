"""Top-level --help for ``scripts/horizon2_generative.py`` (no torch import at module load)."""

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

import horizon2_generative as h2g  # noqa: E402


class TestHorizon2GenerativeHelp(unittest.TestCase):
    def test_help_lists_verify_and_epilog_examples(self) -> None:
        out = io.StringIO()
        err = io.StringIO()
        with patch.object(sys, "argv", ["horizon2_generative.py", "-h"]):
            with patch.object(sys, "stdout", out), patch.object(sys, "stderr", err):
                with self.assertRaises(SystemExit) as ctx:
                    h2g.parse_args()
        self.assertEqual(ctx.exception.code, 0)
        combined = out.getvalue() + err.getvalue()
        self.assertIn("--verify", combined)
        self.assertIn("--smoke", combined)
        self.assertIn("optional-requirements-horizon2.txt", combined)
        self.assertIn("--task grounded", combined)


if __name__ == "__main__":
    unittest.main()
