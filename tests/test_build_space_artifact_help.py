"""Top-level --help for ``scripts/build_space_artifact.py`` (stdlib only)."""

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

import build_space_artifact as bsa  # noqa: E402


class TestBuildSpaceArtifactHelp(unittest.TestCase):
    def test_help_lists_required_flags_and_examples(self) -> None:
        out = io.StringIO()
        err = io.StringIO()
        with patch.object(sys, "argv", ["build_space_artifact.py", "-h"]):
            with patch.object(sys, "stdout", out), patch.object(sys, "stderr", err):
                with self.assertRaises(SystemExit) as ctx:
                    bsa.parse_args()
        self.assertEqual(ctx.exception.code, 0)
        combined = out.getvalue() + err.getvalue()
        self.assertIn("--namespace", combined)
        self.assertIn("--output-dir", combined)
        self.assertIn("TinyModel1Space-bundle", combined)
        self.assertIn("--model-id", combined)


if __name__ == "__main__":
    unittest.main()
