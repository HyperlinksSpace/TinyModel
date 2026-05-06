"""Top-level --help for ``scripts/horizon9_policy_smoke.py`` (stdlib only)."""

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

import horizon9_policy_smoke as h9  # noqa: E402


class TestHorizon9TopLevelHelp(unittest.TestCase):
    def test_help_lists_verify_policy_output(self) -> None:
        out = io.StringIO()
        err = io.StringIO()
        with patch.object(sys, "argv", ["horizon9_policy_smoke.py", "-h"]):
            with patch.object(sys, "stdout", out), patch.object(sys, "stderr", err):
                with self.assertRaises(SystemExit) as ctx:
                    h9.parse_args()
        self.assertEqual(ctx.exception.code, 0)
        combined = out.getvalue() + err.getvalue()
        self.assertIn("--verify", combined)
        self.assertIn("--policy", combined)
        self.assertIn("--output-json", combined)


if __name__ == "__main__":
    unittest.main()
