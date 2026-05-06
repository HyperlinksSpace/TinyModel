"""Top-level --help for ``scripts/horizon1_verify_short_term_a.py`` (no subprocess chain)."""

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

import horizon1_verify_short_term_a as h1a  # noqa: E402


class TestHorizon1VerifyShortTermAHelp(unittest.TestCase):
    def test_help_lists_skip_phase3(self) -> None:
        out = io.StringIO()
        err = io.StringIO()
        with patch.object(sys, "argv", ["horizon1_verify_short_term_a.py", "-h"]):
            with patch.object(sys, "stdout", out), patch.object(sys, "stderr", err):
                with self.assertRaises(SystemExit) as ctx:
                    h1a.parse_args()
        self.assertEqual(ctx.exception.code, 0)
        combined = out.getvalue() + err.getvalue()
        self.assertIn("--skip-phase3", combined)
        self.assertIn("horizon1-verify-a", combined)


if __name__ == "__main__":
    unittest.main()
