"""CLI smoke for ``scripts/routing_policy.py`` (stdlib only; no torch)."""

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

import routing_policy as rp  # noqa: E402


class TestRoutingPolicyHelp(unittest.TestCase):
    def test_help_epilog_lists_examples(self) -> None:
        out = io.StringIO()
        err = io.StringIO()
        with patch.object(sys, "argv", ["routing_policy.py", "-h"]):
            with patch.object(sys, "stdout", out), patch.object(sys, "stderr", err):
                with self.assertRaises(SystemExit) as ctx:
                    rp.parse_args()
        self.assertEqual(ctx.exception.code, 0)
        combined = out.getvalue() + err.getvalue()
        self.assertIn("--demo", combined)
        self.assertIn("--from-checkpoint", combined)
        self.assertIn(".tmp/phase2-smoke", combined)


if __name__ == "__main__":
    unittest.main()
