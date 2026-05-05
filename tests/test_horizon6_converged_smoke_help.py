"""Top-level --help for ``scripts/horizon6_converged_smoke.py`` (stdlib only)."""

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

import horizon6_converged_smoke as h6  # noqa: E402


class TestHorizon6TopLevelHelp(unittest.TestCase):
    def test_help_epilog_lists_verify_and_rag(self) -> None:
        out = io.StringIO()
        err = io.StringIO()
        with patch.object(sys, "argv", ["horizon6_converged_smoke.py", "-h"]):
            with patch.object(sys, "stdout", out), patch.object(sys, "stderr", err):
                with self.assertRaises(SystemExit) as ctx:
                    h6.parse_args()
        self.assertEqual(ctx.exception.code, 0)
        combined = out.getvalue() + err.getvalue()
        self.assertIn("--verify", combined)
        self.assertIn("--with-rag", combined)
        self.assertIn("--output-json", combined)


if __name__ == "__main__":
    unittest.main()
