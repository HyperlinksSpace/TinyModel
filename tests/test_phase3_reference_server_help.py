"""Top-level --help for ``scripts/phase3_reference_server.py`` (no torch until ``main()``)."""

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

import phase3_reference_server as p3srv  # noqa: E402


class TestPhase3ReferenceServerHelp(unittest.TestCase):
    def test_help_lists_model_port_and_swagger(self) -> None:
        out = io.StringIO()
        err = io.StringIO()
        with patch.object(sys, "argv", ["phase3_reference_server.py", "-h"]):
            with patch.object(sys, "stdout", out), patch.object(sys, "stderr", err):
                with self.assertRaises(SystemExit) as ctx:
                    p3srv.parse_args()
        self.assertEqual(ctx.exception.code, 0)
        combined = out.getvalue() + err.getvalue()
        self.assertIn("--model", combined)
        self.assertIn("8765", combined)
        self.assertIn("TINYMODEL_PATH", combined)
        self.assertIn("optional-requirements-phase3.txt", combined)


if __name__ == "__main__":
    unittest.main()
