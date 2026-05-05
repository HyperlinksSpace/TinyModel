"""Top-level --help for ``scripts/horizon4_multimodal.py`` (no torch import at module load)."""

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

import horizon4_multimodal as h4  # noqa: E402


class TestHorizon4TopLevelHelp(unittest.TestCase):
    def test_help_epilog_lists_verify_modes(self) -> None:
        out = io.StringIO()
        err = io.StringIO()
        with patch.object(sys, "argv", ["horizon4_multimodal.py", "-h"]):
            with patch.object(sys, "stdout", out), patch.object(sys, "stderr", err):
                with self.assertRaises(SystemExit) as ctx:
                    h4.parse_args()
        self.assertEqual(ctx.exception.code, 0)
        combined = out.getvalue() + err.getvalue()
        self.assertIn("--verify", combined)
        self.assertIn("--verify-pretrained", combined)
        self.assertIn("--image", combined)


if __name__ == "__main__":
    unittest.main()
